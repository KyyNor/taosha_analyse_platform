# Wide Table Numeric Physical Type Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store numeric FraudHunter wide-table indicator columns as PostgreSQL `DOUBLE PRECISION`, safely convert string indicator values during wide-table generation, and remove unnecessary numeric casts from model execution for typed tables.

**Architecture:** Keep all existing indicator task SQL unchanged. Add a small shared numeric type helper used by offline wide-table SQL generation, realtime DataFrame writes, PG table DDL, dry-run validation, and RuleEngine SQL generation. This plan does not enable or modify the incremental sync path.

**Tech Stack:** FastAPI backend, SQLAlchemy, PostgreSQL, Spark SQL, pandas, pytest.

---

## Scope

In scope:
- Offline full wide-table generation uses `DOUBLE PRECISION` for numeric indicator columns.
- Offline Spark PIVOT SQL converts numeric indicator strings to `DOUBLE` safely.
- Realtime wide-table writes convert numeric pandas columns to floats or nulls before COPY.
- RuleEngine skips `::DOUBLE PRECISION` for numeric indicators when the caller opts into typed wide-table SQL.
- Indicator dry-run reports numeric conversion quality on samples.
- Unit tests for helper behavior and generated SQL.

Out of scope:
- Incremental sync correctness fixes.
- Date physical typing.
- Historical migration of old wide-table versions.
- Changing existing indicator task SQL.
- Changing the model rule DSL.

## File Structure

- Create `backend/services/fraudhunter/wide_table_service/numeric_type_utils.py`  
  Shared numeric metadata detection, PostgreSQL column type resolution, Spark safe-cast SQL generation, pandas conversion, and sample conversion stats.

- Modify `backend/utils/analyze_db_utils.py`  
  Use the shared helper when creating wide-table columns. Keep non-numeric columns on the existing varchar/text behavior.

- Modify `backend/services/fraudhunter/wide_table_service/sync_service.py`  
  Use shared helper in `_build_pivot_sql()` and `_build_pivot_sql_inc()` so generated Spark SQL emits typed numeric columns.

- Modify `backend/services/scheduler/jobs/realtime_indicator_job.py`  
  Convert numeric columns in `final_result` before `batch_insert_copy()`.

- Modify `backend/services/fraudhunter/model_service/rule_engine.py`  
  Add an opt-in `numeric_columns_are_typed` flag to SQL generation so model execution can generate `COALESCE(col, 0)` instead of `COALESCE(col::DOUBLE PRECISION, 0)`.

- Modify `backend/services/fraudhunter/model_service/model_executor.py` and `backend/services/scheduler/jobs/realtime_indicator_job.py`  
  Pass `numeric_columns_are_typed=True` for offline/real-time model execution paths that read newly generated typed wide tables.

- Modify `backend/services/fraudhunter/dry_run_task_service/indicator_executor.py`  
  Add numeric conversion stats to dry-run output without blocking existing task SQL.

- Create `tests/backend/modules/wide_table_sync/test_numeric_type_utils.py`  
  Pure unit tests for numeric safe-cast SQL, PG type resolution, pandas conversion, and dry-run stats.

- Create `tests/backend/modules/wide_table_sync/test_typed_pivot_sql.py`  
  Unit tests for generated full and incremental PIVOT SQL strings.

- Create `tests/backend/modules/model_executor/test_rule_engine_typed_numeric_sql.py`  
  Unit tests for RuleEngine cast removal behavior using a fake indicator cache.

---

### Task 1: Add Numeric Type Utility

**Files:**
- Create: `backend/services/fraudhunter/wide_table_service/numeric_type_utils.py`
- Test: `tests/backend/modules/wide_table_sync/test_numeric_type_utils.py`

- [ ] **Step 1: Write failing tests for numeric metadata and SQL helpers**

Create `tests/backend/modules/wide_table_sync/test_numeric_type_utils.py`:

```python
import sys
from pathlib import Path

import pandas as pd

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

from services.fraudhunter.wide_table_service.numeric_type_utils import (
    NumericConversionStats,
    WideTableNumericTypeHelper,
)


class TestWideTableNumericTypeHelper:
    def test_is_numeric_meta_true_for_numeric(self):
        meta = {"indicator_code": "i_amt", "data_type": "numeric"}
        assert WideTableNumericTypeHelper.is_numeric_meta(meta) is True

    def test_is_numeric_meta_false_for_non_numeric(self):
        meta = {"indicator_code": "i_name", "data_type": "string"}
        assert WideTableNumericTypeHelper.is_numeric_meta(meta) is False

    def test_pg_type_for_numeric_is_double_precision(self):
        meta = {"indicator_code": "i_amt", "data_type": "numeric"}
        assert WideTableNumericTypeHelper.pg_type_for_indicator(meta, []) == "DOUBLE PRECISION"

    def test_pg_type_for_non_numeric_keeps_existing_varchar_behavior(self):
        meta = {"indicator_code": "i_name", "data_type": "string"}
        assert WideTableNumericTypeHelper.pg_type_for_indicator(meta, []) == "varchar(1000)"

    def test_pg_type_for_long_text_stays_text(self):
        meta = {"indicator_code": "i_desc", "data_type": "string"}
        assert WideTableNumericTypeHelper.pg_type_for_indicator(meta, ["i_desc"]) == "text"

    def test_spark_numeric_safe_cast_expression_handles_blank_and_invalid_values(self):
        expr = WideTableNumericTypeHelper.spark_select_expression(
            {"indicator_code": "i_amt", "data_type": "numeric"}
        )
        assert "CASE" in expr
        assert "TRIM(CAST(i_amt AS STRING)) = ''" in expr
        assert "RLIKE" in expr
        assert "CAST(TRIM(CAST(i_amt AS STRING)) AS DOUBLE)" in expr
        assert "AS i_amt" in expr

    def test_spark_non_numeric_expression_passes_column_through(self):
        expr = WideTableNumericTypeHelper.spark_select_expression(
            {"indicator_code": "i_name", "data_type": "string"}
        )
        assert expr == "i_name"

    def test_convert_numeric_dataframe_columns_turns_blank_invalid_to_null(self):
        df = pd.DataFrame({
            "target_id": ["a", "b", "c", "d"],
            "i_amt": ["12.5", "", "  ", "not-a-number"],
            "i_name": ["x", "y", "z", "w"],
        })
        metadata = {
            "1": {"indicator_code": "i_amt", "data_type": "numeric"},
            "2": {"indicator_code": "i_name", "data_type": "string"},
        }

        converted, stats = WideTableNumericTypeHelper.convert_numeric_dataframe_columns(df, metadata)

        assert converted["i_amt"].tolist()[0] == 12.5
        assert pd.isna(converted["i_amt"].tolist()[1])
        assert pd.isna(converted["i_amt"].tolist()[2])
        assert pd.isna(converted["i_amt"].tolist()[3])
        assert converted["i_name"].tolist() == ["x", "y", "z", "w"]
        assert stats == [NumericConversionStats(indicator_code="i_amt", blank_count=2, invalid_count=1)]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/backend/modules/wide_table_sync/test_numeric_type_utils.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `numeric_type_utils`.

- [ ] **Step 3: Implement the helper**

Create `backend/services/fraudhunter/wide_table_service/numeric_type_utils.py`:

```python
"""Utilities for typed numeric FraudHunter wide-table columns."""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd


NUMERIC_REGEX_SPARK = r"^-?(\\d+(\\.\\d*)?|\\.\\d+)([eE][+-]?\\d+)?$"


@dataclass(frozen=True)
class NumericConversionStats:
    indicator_code: str
    blank_count: int
    invalid_count: int


class WideTableNumericTypeHelper:
    """Centralizes numeric physical-type behavior for wide-table generation."""

    @staticmethod
    def is_numeric_meta(meta: Dict[str, Any]) -> bool:
        return str(meta.get("data_type") or "").lower() == "numeric"

    @staticmethod
    def pg_type_for_indicator(meta: Dict[str, Any], long_text_indicator_list: Iterable[str]) -> str:
        indicator_code = meta.get("indicator_code")
        if WideTableNumericTypeHelper.is_numeric_meta(meta):
            return "DOUBLE PRECISION"
        if indicator_code in set(long_text_indicator_list):
            return "text"
        return "varchar(1000)"

    @staticmethod
    def numeric_indicator_codes(indicator_metadata: Dict[Any, Dict[str, Any]]) -> List[str]:
        return [
            meta.get("indicator_code")
            for meta in indicator_metadata.values()
            if meta.get("indicator_code") and WideTableNumericTypeHelper.is_numeric_meta(meta)
        ]

    @staticmethod
    def spark_select_expression(meta: Dict[str, Any]) -> str:
        code = meta.get("indicator_code")
        if not code:
            raise ValueError("indicator_code is required")

        if not WideTableNumericTypeHelper.is_numeric_meta(meta):
            return code

        value_sql = f"TRIM(CAST({code} AS STRING))"
        return (
            "CASE "
            f"WHEN {code} IS NULL OR {value_sql} = '' THEN CAST(NULL AS DOUBLE) "
            f"WHEN {value_sql} RLIKE '{NUMERIC_REGEX_SPARK}' THEN CAST({value_sql} AS DOUBLE) "
            "ELSE CAST(NULL AS DOUBLE) "
            f"END AS {code}"
        )

    @staticmethod
    def spark_select_expressions(indicator_metadata: Dict[Any, Dict[str, Any]]) -> List[str]:
        return [
            WideTableNumericTypeHelper.spark_select_expression(meta)
            for meta in indicator_metadata.values()
            if meta.get("indicator_code")
        ]

    @staticmethod
    def convert_numeric_dataframe_columns(
        df: pd.DataFrame,
        indicator_metadata: Dict[Any, Dict[str, Any]],
    ) -> Tuple[pd.DataFrame, List[NumericConversionStats]]:
        converted = df.copy()
        stats: List[NumericConversionStats] = []

        for code in WideTableNumericTypeHelper.numeric_indicator_codes(indicator_metadata):
            if code not in converted.columns:
                continue

            raw = converted[code]
            as_text = raw.astype("string")
            stripped = as_text.str.strip()
            blank_mask = raw.isna() | stripped.eq("")
            numeric_values = pd.to_numeric(stripped.mask(blank_mask), errors="coerce")
            invalid_mask = numeric_values.isna() & ~blank_mask

            converted[code] = numeric_values.astype("float64")
            stats.append(
                NumericConversionStats(
                    indicator_code=code,
                    blank_count=int(blank_mask.sum()),
                    invalid_count=int(invalid_mask.sum()),
                )
            )

        return converted, stats
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/backend/modules/wide_table_sync/test_numeric_type_utils.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/fraudhunter/wide_table_service/numeric_type_utils.py tests/backend/modules/wide_table_sync/test_numeric_type_utils.py
git commit -m "feat: add wide table numeric type helper"
```

---

### Task 2: Use DOUBLE PRECISION When Creating Wide Tables

**Files:**
- Modify: `backend/utils/analyze_db_utils.py`
- Test: `tests/backend/modules/wide_table_sync/test_numeric_type_utils.py`

- [ ] **Step 1: Add failing test for PG column definitions through existing resolver**

Append to `tests/backend/modules/wide_table_sync/test_numeric_type_utils.py`:

```python
from utils.analyze_db_utils import AnalyzeDBPartitionManager


class TestAnalyzeDBPartitionManagerNumericTypes:
    def test_resolve_indicator_column_def_uses_double_precision_for_numeric(self):
        meta = {"indicator_code": "i_amt", "data_type": "numeric"}
        assert AnalyzeDBPartitionManager.resolve_indicator_column_def(meta, []) == (
            "i_amt",
            "DOUBLE PRECISION",
        )

    def test_resolve_indicator_column_def_keeps_text_for_long_text_non_numeric(self):
        meta = {"indicator_code": "i_desc", "data_type": "string"}
        assert AnalyzeDBPartitionManager.resolve_indicator_column_def(meta, ["i_desc"]) == (
            "i_desc",
            "text",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/backend/modules/wide_table_sync/test_numeric_type_utils.py::TestAnalyzeDBPartitionManagerNumericTypes -v
```

Expected: FAIL with `AttributeError: type object 'AnalyzeDBPartitionManager' has no attribute 'resolve_indicator_column_def'`.

- [ ] **Step 3: Implement DDL resolver and wire it into table creation**

Modify `backend/utils/analyze_db_utils.py`:

```python
from services.fraudhunter.wide_table_service.numeric_type_utils import WideTableNumericTypeHelper
```

Add this method inside `AnalyzeDBPartitionManager` near `_resolve_pg_column_def`:

```python
    @classmethod
    def resolve_indicator_column_def(cls, meta: Dict[str, Any], long_text_list: list) -> tuple:
        indicator_code = meta.get("indicator_code")
        if not indicator_code:
            raise ValueError("indicator_code is required")
        return (
            indicator_code,
            WideTableNumericTypeHelper.pg_type_for_indicator(meta, long_text_list),
        )
```

In both `create_wide_table()` and `create_heap_table()`, replace the indicator-column append block:

```python
                columns.append(
                    AnalyzeDBPartitionManager._resolve_pg_column_def(
                        indicator_code, long_text_indicator_list
                    )
                )
```

with:

```python
                columns.append(
                    AnalyzeDBPartitionManager.resolve_indicator_column_def(
                        meta, long_text_indicator_list
                    )
                )
```

Keep target/system columns using `_resolve_pg_column_def('target_id', [])` and `_resolve_pg_column_def('etl_date', [])`.

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest tests/backend/modules/wide_table_sync/test_numeric_type_utils.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/utils/analyze_db_utils.py tests/backend/modules/wide_table_sync/test_numeric_type_utils.py
git commit -m "feat: create numeric wide table columns as double precision"
```

---

### Task 3: Type Numeric Columns in Offline Full PIVOT SQL

**Files:**
- Modify: `backend/services/fraudhunter/wide_table_service/sync_service.py`
- Test: `tests/backend/modules/wide_table_sync/test_typed_pivot_sql.py`

- [ ] **Step 1: Write failing tests for generated PIVOT SQL**

Create `tests/backend/modules/wide_table_sync/test_typed_pivot_sql.py`:

```python
import sys
from datetime import date
from pathlib import Path

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

from services.fraudhunter.wide_table_service.sync_service import WideTableSyncService


def _service():
    service = WideTableSyncService()
    service.source_table = "source_indicator_vertical"
    return service


class TestTypedPivotSql:
    def test_full_pivot_casts_numeric_columns_and_keeps_text_columns(self):
        metadata = {
            "1": {"indicator_code": "i_amt", "data_type": "numeric"},
            "2": {"indicator_code": "i_name", "data_type": "string"},
        }

        sql = _service()._build_pivot_sql("dep_acct_wide_table", metadata, date(2026, 6, 18))

        assert "FROM (" in sql
        assert "PIVOT" in sql
        assert "CASE WHEN i_amt IS NULL" in sql
        assert "CAST(TRIM(CAST(i_amt AS STRING)) AS DOUBLE)" in sql
        assert "END AS i_amt" in sql
        assert "i_name" in sql
        assert "'2026-06-18' as etl_date" in sql

    def test_incremental_pivot_casts_only_incremental_numeric_columns(self):
        metadata = {
            "1": {"indicator_code": "i_amt", "data_type": "numeric"},
            "2": {"indicator_code": "i_name", "data_type": "string"},
        }

        sql = _service()._build_pivot_sql_inc(
            "dep_acct_wide_table",
            metadata,
            date(2026, 6, 18),
            ["i_amt"],
        )

        assert "indicator_id IN ('i_amt')" in sql
        assert "CASE WHEN i_amt IS NULL" in sql
        assert "i_name" not in sql
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/backend/modules/wide_table_sync/test_typed_pivot_sql.py -v
```

Expected: FAIL because `_build_pivot_sql()` and `_build_pivot_sql_inc()` still select raw PIVOT columns.

- [ ] **Step 3: Implement typed outer SELECT in PIVOT SQL builders**

Modify `backend/services/fraudhunter/wide_table_service/sync_service.py`:

```python
from services.fraudhunter.wide_table_service.numeric_type_utils import WideTableNumericTypeHelper
```

Add private helper methods to `WideTableSyncService`:

```python
    @staticmethod
    def _metadata_for_codes(indicator_metadata: dict, indicator_codes: list) -> dict:
        indicator_code_set = set(indicator_codes)
        return {
            key: meta
            for key, meta in indicator_metadata.items()
            if meta.get("indicator_code") in indicator_code_set
        }

    def _build_typed_pivot_outer_select(
        self,
        pivot_sql: str,
        indicator_metadata: dict,
        etl_date: date,
    ) -> str:
        select_columns = [
            "target_id",
            *WideTableNumericTypeHelper.spark_select_expressions(indicator_metadata),
            f"'{etl_date.strftime('%Y-%m-%d')}' as etl_date",
        ]
        select_clause = ",\n    ".join(select_columns)
        return f"""
SELECT
    {select_clause}
FROM (
{pivot_sql}
) AS pivot_result
""".strip()
```

In `_build_pivot_sql()`, keep the existing inner PIVOT generation but remove the outer `SELECT target_id, {select_columns}, '{etl_date}' as etl_date`. The inner SQL should return `target_id` plus raw pivoted indicator columns only. Then return:

```python
        return self._build_typed_pivot_outer_select(
            pivot_sql=inner_sql,
            indicator_metadata=indicator_metadata,
            etl_date=etl_date,
        )
```

In `_build_pivot_sql_inc()`, filter metadata before building the typed outer select:

```python
        inc_metadata = self._metadata_for_codes(indicator_metadata, inc_codes)
        return self._build_typed_pivot_outer_select(
            pivot_sql=inner_sql,
            indicator_metadata=inc_metadata,
            etl_date=etl_date,
        )
```

Preserve the current `indicator_id IN (...)` filter in incremental SQL.

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest tests/backend/modules/wide_table_sync/test_typed_pivot_sql.py tests/backend/modules/wide_table_sync/test_numeric_type_utils.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/fraudhunter/wide_table_service/sync_service.py tests/backend/modules/wide_table_sync/test_typed_pivot_sql.py
git commit -m "feat: safe cast numeric columns during wide table pivot"
```

---

### Task 4: Convert Realtime Numeric DataFrame Columns Before COPY

**Files:**
- Modify: `backend/services/scheduler/jobs/realtime_indicator_job.py`
- Test: `tests/backend/modules/wide_table_sync/test_numeric_type_utils.py`

- [ ] **Step 1: Add a unit test for realtime conversion reuse**

Append to `tests/backend/modules/wide_table_sync/test_numeric_type_utils.py`:

```python
class TestRealtimeNumericConversion:
    def test_realtime_numeric_conversion_reuses_helper_contract(self):
        df = pd.DataFrame({
            "target_id": ["acct1", "acct2"],
            "i_dep_acct_no_realtime_00001": ["100.25", ""],
        })
        metadata = {
            "10": {
                "indicator_code": "i_dep_acct_no_realtime_00001",
                "data_type": "numeric",
            }
        }

        converted, stats = WideTableNumericTypeHelper.convert_numeric_dataframe_columns(df, metadata)

        assert converted["i_dep_acct_no_realtime_00001"].tolist()[0] == 100.25
        assert pd.isna(converted["i_dep_acct_no_realtime_00001"].tolist()[1])
        assert stats[0].blank_count == 1
        assert stats[0].invalid_count == 0
```

- [ ] **Step 2: Run test to verify helper behavior**

Run:

```bash
uv run pytest tests/backend/modules/wide_table_sync/test_numeric_type_utils.py::TestRealtimeNumericConversion -v
```

Expected: PASS.

- [ ] **Step 3: Wire realtime job to convert before COPY**

Modify `backend/services/scheduler/jobs/realtime_indicator_job.py`:

```python
from services.fraudhunter.wide_table_service.numeric_type_utils import WideTableNumericTypeHelper
```

In `step1_generate_realtime_indicators()`, after:

```python
        final_result['etl_date'] = today
        final_result['run_time'] = half_hour_slot
```

add:

```python
        final_result, numeric_stats = WideTableNumericTypeHelper.convert_numeric_dataframe_columns(
            final_result,
            current_version.indicator_metadata or {},
        )
        for stat in numeric_stats:
            if stat.blank_count or stat.invalid_count:
                logger.info(
                    f"[{object_type}] 数值指标转换: {stat.indicator_code}, "
                    f"空值={stat.blank_count}, 非法值={stat.invalid_count}"
                )
```

- [ ] **Step 4: Run affected tests**

Run:

```bash
uv run pytest tests/backend/modules/wide_table_sync/test_numeric_type_utils.py tests/backend/modules/realtime_indicator/test_compute_half_hour_slot.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/scheduler/jobs/realtime_indicator_job.py tests/backend/modules/wide_table_sync/test_numeric_type_utils.py
git commit -m "feat: convert realtime numeric columns before copy"
```

---

### Task 5: Remove Numeric Casts for Typed Wide-Table Model SQL

**Files:**
- Modify: `backend/services/fraudhunter/model_service/rule_engine.py`
- Modify: `backend/services/fraudhunter/model_service/model_executor.py`
- Modify: `backend/services/scheduler/jobs/realtime_indicator_job.py`
- Test: `tests/backend/modules/model_executor/test_rule_engine_typed_numeric_sql.py`

- [ ] **Step 1: Write failing RuleEngine unit tests using a fake cache**

Create `tests/backend/modules/model_executor/test_rule_engine_typed_numeric_sql.py`:

```python
import sys
from pathlib import Path
from types import SimpleNamespace

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

from services.fraudhunter.model_service.rule_engine import RuleEngine


class TestRuleEngineTypedNumericSql:
    def test_numeric_sql_skips_cast_when_typed_flag_is_true(self):
        engine = RuleEngine(db=None)
        engine._indicator_cache["i_amt"] = SimpleNamespace(data_type="numeric")

        sql = engine._get_indicator_sql_with_cast(
            "i_amt",
            {"i_amt": "dep_acct_realtime_indicator"},
            numeric_columns_are_typed=True,
        )

        assert sql == "COALESCE(dep_acct_realtime_indicator.i_amt, 0)"

    def test_numeric_sql_keeps_cast_when_typed_flag_is_false(self):
        engine = RuleEngine(db=None)
        engine._indicator_cache["i_amt"] = SimpleNamespace(data_type="numeric")

        sql = engine._get_indicator_sql_with_cast(
            "i_amt",
            {"i_amt": "dep_acct_realtime_indicator"},
            numeric_columns_are_typed=False,
        )

        assert sql == "COALESCE(dep_acct_realtime_indicator.i_amt::DOUBLE PRECISION, 0)"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/backend/modules/model_executor/test_rule_engine_typed_numeric_sql.py -v
```

Expected: FAIL because `_get_indicator_sql_with_cast()` does not accept `numeric_columns_are_typed`.

- [ ] **Step 3: Add typed numeric flag through RuleEngine SQL generation**

Modify method signatures in `backend/services/fraudhunter/model_service/rule_engine.py`:

```python
    def _get_indicator_sql_with_cast(
        self,
        indicator_code: str,
        indicator_alias_mapping: Optional[Dict[str, str]] = None,
        numeric_columns_are_typed: bool = False,
    ) -> str:
```

Change numeric handling:

```python
        if indicator and indicator.data_type == 'numeric':
            if numeric_columns_are_typed:
                return f"COALESCE({base_sql}, 0)"
            return f"COALESCE({base_sql}::DOUBLE PRECISION, 0)"
```

Thread the same flag through `_value_expression_to_sql()` and `generate_sql_expression()`:

```python
    def _value_expression_to_sql(
        self,
        value_expr: ValueExpression,
        indicator_alias_mapping: Optional[Dict[str, str]] = None,
        use_display_name: bool = False,
        numeric_columns_are_typed: bool = False,
    ) -> str:
```

Every internal call to `_get_indicator_sql_with_cast(...)` inside `_value_expression_to_sql()` must pass `numeric_columns_are_typed=numeric_columns_are_typed`.

Update `generate_sql_expression()`:

```python
    def generate_sql_expression(
        self,
        rule_config: RuleConfig,
        indicator_alias_mapping: Optional[Dict[str, str]] = None,
        use_display_name: bool = False,
        numeric_columns_are_typed: bool = False,
    ) -> str:
```

Inside `condition_to_sql()`, call:

```python
                left_sql = self._get_indicator_sql_with_cast(
                    indicator,
                    indicator_alias_mapping,
                    numeric_columns_are_typed=numeric_columns_are_typed,
                )
```

When generating the right side:

```python
                right_sql = self._value_expression_to_sql(
                    value_expr,
                    indicator_alias_mapping,
                    use_display_name,
                    numeric_columns_are_typed=numeric_columns_are_typed,
                )
```

When recursively expanding `ModelReferenceRule`, pass the same flag to `generate_sql_expression()`.

- [ ] **Step 4: Opt model execution into typed numeric SQL**

In `backend/services/fraudhunter/model_service/model_executor.py`, update `_generate_backtest_sql()`:

```python
        where_clause = rule_engine.generate_sql_expression(
            rule_config,
            indicator_alias_mapping,
            numeric_columns_are_typed=True,
        )
```

In `backend/services/scheduler/jobs/realtime_indicator_job.py`, update `_build_model_matching_sql()`:

```python
        where_condition = rule_engine.generate_sql_expression(
            rule_config,
            indicator_alias_mapping,
            numeric_columns_are_typed=True,
        )
```

Do not change preview/display calls that use `use_display_name=True`.

- [ ] **Step 5: Run tests**

Run:

```bash
uv run pytest tests/backend/modules/model_executor/test_rule_engine_typed_numeric_sql.py tests/backend/modules/model_executor/test_backtest_cust_realtime.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/services/fraudhunter/model_service/rule_engine.py backend/services/fraudhunter/model_service/model_executor.py backend/services/scheduler/jobs/realtime_indicator_job.py tests/backend/modules/model_executor/test_rule_engine_typed_numeric_sql.py
git commit -m "feat: skip numeric casts for typed wide table model sql"
```

---

### Task 6: Add Numeric Conversion Stats to Indicator Dry Run

**Files:**
- Modify: `backend/services/fraudhunter/dry_run_task_service/indicator_executor.py`
- Test: `tests/backend/modules/wide_table_sync/test_numeric_type_utils.py`

- [ ] **Step 1: Add pure helper test for dry-run numeric stats**

Append to `tests/backend/modules/wide_table_sync/test_numeric_type_utils.py`:

```python
class TestDryRunNumericStats:
    def test_numeric_stats_can_be_serialized_for_api_response(self):
        stats = [NumericConversionStats(indicator_code="i_amt", blank_count=1, invalid_count=2)]
        payload = [stat.__dict__ for stat in stats]
        assert payload == [{"indicator_code": "i_amt", "blank_count": 1, "invalid_count": 2}]
```

- [ ] **Step 2: Run test**

Run:

```bash
uv run pytest tests/backend/modules/wide_table_sync/test_numeric_type_utils.py::TestDryRunNumericStats -v
```

Expected: PASS.

- [ ] **Step 3: Wire dry-run response to include conversion stats**

Modify `backend/services/fraudhunter/dry_run_task_service/indicator_executor.py`:

```python
from services.fraudhunter.wide_table_service.numeric_type_utils import WideTableNumericTypeHelper
```

In `execute_dry_run()`, after `result = await self._spark_execution(...)`, add:

```python
            numeric_conversion_stats = []
            if indicator_ids:
                indicators_for_stats = db.query(FraudHunterIndicatorDefinition).filter(
                    FraudHunterIndicatorDefinition.id.in_(indicator_ids)
                ).all()
                stats_metadata = {
                    str(ind.id): {
                        "indicator_code": ind.indicator_code,
                        "data_type": ind.data_type,
                    }
                    for ind in indicators_for_stats
                }
                _, conversion_stats = WideTableNumericTypeHelper.convert_numeric_dataframe_columns(
                    pd.DataFrame(result["sample_result"]),
                    stats_metadata,
                )
                numeric_conversion_stats = [stat.__dict__ for stat in conversion_stats]
```

In the returned dict, add:

```python
                'numeric_conversion_stats': numeric_conversion_stats,
```

Do not mutate `sample_result`; dry-run should still show raw task output for user debugging.

- [ ] **Step 4: Run targeted tests**

Run:

```bash
uv run pytest tests/backend/modules/wide_table_sync/test_numeric_type_utils.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/fraudhunter/dry_run_task_service/indicator_executor.py tests/backend/modules/wide_table_sync/test_numeric_type_utils.py
git commit -m "feat: report dry run numeric conversion stats"
```

---

### Task 7: Full Verification

**Files:**
- All files changed in Tasks 1-6.

- [ ] **Step 1: Run backend unit tests for affected modules**

Run:

```bash
uv run pytest \
  tests/backend/modules/wide_table_sync/test_numeric_type_utils.py \
  tests/backend/modules/wide_table_sync/test_typed_pivot_sql.py \
  tests/backend/modules/realtime_indicator/test_compute_half_hour_slot.py \
  tests/backend/modules/model_executor/test_rule_engine_typed_numeric_sql.py \
  tests/backend/modules/model_executor/test_backtest_cust_realtime.py \
  -v
```

Expected: PASS.

- [ ] **Step 2: Run lint or compile check for touched backend files**

Run:

```bash
uv run python -m compileall \
  backend/services/fraudhunter/wide_table_service/numeric_type_utils.py \
  backend/utils/analyze_db_utils.py \
  backend/services/fraudhunter/wide_table_service/sync_service.py \
  backend/services/scheduler/jobs/realtime_indicator_job.py \
  backend/services/fraudhunter/model_service/rule_engine.py \
  backend/services/fraudhunter/model_service/model_executor.py \
  backend/services/fraudhunter/dry_run_task_service/indicator_executor.py
```

Expected: all files compile without syntax errors.

- [ ] **Step 3: Manual SQL inspection**

Run a small Python snippet to print generated SQL:

```bash
uv run python - <<'PY'
from datetime import date
from services.fraudhunter.wide_table_service.sync_service import WideTableSyncService

service = WideTableSyncService()
service.source_table = "source_indicator_vertical"
metadata = {
    "1": {"indicator_code": "i_amt", "data_type": "numeric"},
    "2": {"indicator_code": "i_name", "data_type": "string"},
}
print(service._build_pivot_sql("dep_acct_wide_table", metadata, date(2026, 6, 18)))
PY
```

Expected: SQL contains `CASE WHEN i_amt IS NULL`, `RLIKE`, and `CAST(... AS DOUBLE)`.

- [ ] **Step 4: Final commit if verification required additional edits**

```bash
git add backend tests docs/superpowers/plans/2026-06-19-wide-table-numeric-physical-type.md
git commit -m "test: verify numeric wide table physical type changes"
```

Only run this commit if Task 7 caused additional edits. Otherwise do not create an empty commit.

---

## Rollout Notes

- New typed numeric columns apply only to newly created wide-table versions. Old versions may still be varchar/text.
- Because model execution opts into typed SQL, first deploy should be paired with fresh offline and realtime wide-table generation. If old string wide tables must remain executable, add a config flag such as `fraudhunter_wide_table_numeric_physical_type_enabled` and pass it into RuleEngine instead of hardcoding `True`.
- Empty strings and invalid numeric strings become NULL during wide-table generation.
- Existing model SQL still wraps numeric values with `COALESCE(..., 0)`, preserving current missing-as-zero semantics.
- Incremental sync remains disabled and unchanged in this plan.

## Self-Review

- Spec coverage: This plan covers numeric-only physical typing, offline full PIVOT conversion, realtime conversion, model cast removal, dry-run reporting, and tests. It explicitly excludes incremental sync.
- Placeholder scan: No implementation placeholders are intentionally left in tasks.
- Type consistency: Helper names and signatures are consistent across tasks: `WideTableNumericTypeHelper`, `NumericConversionStats`, `spark_select_expression`, `convert_numeric_dataframe_columns`, and `numeric_columns_are_typed`.
