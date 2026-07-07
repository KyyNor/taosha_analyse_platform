# Wide Table Delta Insert-Select Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the disabled copy/update incremental wide-table path with a delta-table plus PG `INSERT SELECT base LEFT JOIN delta` physicalization path.

**Architecture:** Keep the current full Spark PIVOT path as fallback. For version changes with a reusable base partition, Spark only pivots changed/new indicator columns into a temporary delta table, then PG inserts a new physical wide-table partition by selecting static columns from the base partition and changed/new columns from delta. Snapshot, version readiness, and promotion behavior stay inside the existing `WideTableSyncService` flow.

**Tech Stack:** Python 3, SQLAlchemy, PostgreSQL partitioned tables, PySpark/JDBC existing query writers, pytest.

## Global Constraints

- `target_id` set is stable for the same `object_type` and `etl_date`; use `base LEFT JOIN delta`, not `FULL OUTER JOIN`.
- `target_id` and `etl_date` are selected from the base table, not `COALESCE`.
- Changed and new indicator columns are selected from delta directly; do not fall back to base values.
- Removed indicator columns are excluded from the new target table field list.
- If no reusable base partition exists, use the existing full Spark PIVOT path.
- First implementation does not modify DS workflow generation, realtime wide-table generation, model SQL generation, or version promotion thresholds.

---

## File Structure

- Modify `backend/domain/wide_table/version_delta.py`: extend `VersionDelta` with `removed_cols` and classify removed indicators.
- Create `tests/backend/modules/wide_table_sync/test_version_delta.py`: focused unit tests for diff categories.
- Modify `backend/utils/analyze_db_utils.py`: add SQL-builder and executor helpers for delta insert-select physicalization.
- Create `tests/backend/modules/wide_table_sync/test_delta_insert_select_sql.py`: unit tests for generated PG SQL.
- Modify `backend/services/fraudhunter/wide_table_service/sync_service.py`: replace the disabled copy/update branch with the new delta insert-select branch.
- Modify `tests/backend/modules/wide_table_sync/test_typed_pivot_sql.py`: update stubs if new imports or helper calls require it.

---

### Task 1: Extend Version Delta Classification

**Files:**
- Modify: `backend/domain/wide_table/version_delta.py`
- Create: `tests/backend/modules/wide_table_sync/test_version_delta.py`

**Interfaces:**
- Consumes: `WideTableComparator.diff(current_metadata: Dict[int, dict], target_metadata: Dict[int, dict])`
- Produces: `VersionDelta(static_cols: list[str], changed_cols: list[str], new_cols: list[str], removed_cols: list[str])`

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/modules/wide_table_sync/test_version_delta.py`:

```python
import sys
from pathlib import Path

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

from domain.wide_table.version_delta import VersionDelta, WideTableComparator


class TestVersionDelta:
    def test_mixed_static_changed_new_removed_columns(self):
        current = {
            1: {"version": 1, "indicator_code": "i_static"},
            2: {"version": 1, "indicator_code": "i_changed"},
            3: {"version": 1, "indicator_code": "i_removed"},
        }
        target = {
            1: {"version": 1, "indicator_code": "i_static"},
            2: {"version": 2, "indicator_code": "i_changed"},
            4: {"version": 1, "indicator_code": "i_new"},
        }

        delta = WideTableComparator.diff(current, target)

        assert isinstance(delta, VersionDelta)
        assert delta.static_cols == ["i_static"]
        assert delta.changed_cols == ["i_changed"]
        assert delta.new_cols == ["i_new"]
        assert delta.removed_cols == ["i_removed"]
        assert delta.deferred_cols == ["i_changed", "i_new"]
        assert delta.has_any_change is True

    def test_only_removed_columns_count_as_change(self):
        current = {
            1: {"version": 1, "indicator_code": "i_removed"},
            2: {"version": 1, "indicator_code": "i_static"},
        }
        target = {
            2: {"version": 1, "indicator_code": "i_static"},
        }

        delta = WideTableComparator.diff(current, target)

        assert delta.static_cols == ["i_static"]
        assert delta.changed_cols == []
        assert delta.new_cols == []
        assert delta.removed_cols == ["i_removed"]
        assert delta.has_any_change is True
        assert delta.deferred_cols == []

    def test_unchanged_columns_have_no_change(self):
        current = {1: {"version": 1, "indicator_code": "i_same"}}
        target = {1: {"version": 1, "indicator_code": "i_same"}}

        delta = WideTableComparator.diff(current, target)

        assert delta.static_cols == ["i_same"]
        assert delta.changed_cols == []
        assert delta.new_cols == []
        assert delta.removed_cols == []
        assert delta.has_any_change is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/kyynor/Code/taosha_analyse_platform && pytest -c tests/backend/pytest.ini tests/backend/modules/wide_table_sync/test_version_delta.py -v`

Expected: FAIL with `AttributeError: 'VersionDelta' object has no attribute 'removed_cols'`.

- [ ] **Step 3: Implement removed column classification**

Modify `backend/domain/wide_table/version_delta.py`:

```python
@dataclass
class VersionDelta:
    """两版本之间完整列差异的持有结构。"""
    static_cols: List[str] = field(default_factory=list)
    changed_cols: List[str] = field(default_factory=list)
    new_cols: List[str] = field(default_factory=list)
    removed_cols: List[str] = field(default_factory=list)

    @property
    def is_unchanged(self) -> bool:
        """返回 True 时，增量同步应跳过。"""
        return not (self.changed_cols or self.new_cols or self.removed_cols)

    @property
    def has_any_change(self) -> bool:
        return bool(self.changed_cols or self.new_cols or self.removed_cols)

    @property
    def deferred_cols(self) -> List[str]:
        """需要 PIVOT 重建的列：changed + new。removed 不参与新表字段。"""
        return self.changed_cols + self.new_cols
```

Replace the loop in `WideTableComparator.diff()` with:

```python
        all_keys = set(current_metadata.keys()) | set(target_metadata.keys())
        for k in sorted(all_keys):
            cur_meta = current_metadata.get(k, {})
            tgt_meta = target_metadata.get(k, {})
            cur_ver = cur_meta.get("version")
            tgt_ver = tgt_meta.get("version")
            code = (tgt_meta or cur_meta).get("indicator_code")

            if not code:
                continue

            if k not in target_metadata:
                removed.append(code)
            elif k not in current_metadata:
                new.append(code)
            elif cur_ver is None or tgt_ver is None:
                changed.append(code)
            elif cur_ver == tgt_ver:
                static.append(code)
            else:
                changed.append(code)

        return VersionDelta(
            static_cols=static,
            changed_cols=changed,
            new_cols=new,
            removed_cols=removed,
        )
```

Also initialize `removed: List[str] = []` beside the other lists.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/kyynor/Code/taosha_analyse_platform && pytest -c tests/backend/pytest.ini tests/backend/modules/wide_table_sync/test_version_delta.py -v`

Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/domain/wide_table/version_delta.py tests/backend/modules/wide_table_sync/test_version_delta.py
git commit -m "feat: track removed wide table indicators"
```

---

### Task 2: Add PG Insert-Select SQL Helpers

**Files:**
- Modify: `backend/utils/analyze_db_utils.py`
- Create: `tests/backend/modules/wide_table_sync/test_delta_insert_select_sql.py`

**Interfaces:**
- Consumes: target metadata dict with `indicator_code`.
- Produces:
  - `AnalyzeDBPartitionManager.build_insert_select_from_base_delta_sql(dest_table: str, base_table: str, delta_table: Optional[str], target_metadata: Dict[str, Any], static_cols: list[str], inc_cols: list[str], etl_date: str) -> str`
  - `AnalyzeDBPartitionManager.insert_select_from_base_delta(...) -> int`

- [ ] **Step 1: Write the failing SQL-builder tests**

Create `tests/backend/modules/wide_table_sync/test_delta_insert_select_sql.py`:

```python
import sys
from pathlib import Path

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

from utils.analyze_db_utils import AnalyzeDBPartitionManager


class TestDeltaInsertSelectSql:
    def test_build_insert_select_uses_left_join_and_base_keys(self):
        metadata = {
            "1": {"indicator_code": "i_static"},
            "2": {"indicator_code": "i_changed"},
            "3": {"indicator_code": "i_new"},
        }

        sql = AnalyzeDBPartitionManager.build_insert_select_from_base_delta_sql(
            dest_table="dep_acct_wide_table_new",
            base_table="dep_acct_wide_table_old_20260707",
            delta_table="_delta_dep_acct_wide_table_new_20260707",
            target_metadata=metadata,
            static_cols=["i_static"],
            inc_cols=["i_changed", "i_new"],
            etl_date="2026-07-07",
        )

        assert "INSERT INTO dep_acct_wide_table_new" in sql
        assert "target_id, i_static, i_changed, i_new, etl_date" in sql
        assert "b.target_id" in sql
        assert "b.etl_date" in sql
        assert "b.i_static" in sql
        assert "d.i_changed" in sql
        assert "d.i_new" in sql
        assert "LEFT JOIN _delta_dep_acct_wide_table_new_20260707 d" in sql
        assert "COALESCE" not in sql
        assert "FULL OUTER JOIN" not in sql

    def test_build_insert_select_without_delta_for_removed_only_change(self):
        metadata = {
            "1": {"indicator_code": "i_static"},
        }

        sql = AnalyzeDBPartitionManager.build_insert_select_from_base_delta_sql(
            dest_table="cust_wide_table_new",
            base_table="cust_wide_table_old_20260707",
            delta_table=None,
            target_metadata=metadata,
            static_cols=["i_static"],
            inc_cols=[],
            etl_date="2026-07-07",
        )

        assert "INSERT INTO cust_wide_table_new" in sql
        assert "target_id, i_static, etl_date" in sql
        assert "b.i_static" in sql
        assert "JOIN" not in sql
        assert "COALESCE" not in sql
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/kyynor/Code/taosha_analyse_platform && pytest -c tests/backend/pytest.ini tests/backend/modules/wide_table_sync/test_delta_insert_select_sql.py -v`

Expected: FAIL with `AttributeError: type object 'AnalyzeDBPartitionManager' has no attribute 'build_insert_select_from_base_delta_sql'`.

- [ ] **Step 3: Implement SQL-builder and executor**

Add these methods inside `AnalyzeDBPartitionManager` in `backend/utils/analyze_db_utils.py` after `merge_aux_into_main`:

```python
    @staticmethod
    def _indicator_codes_in_metadata_order(indicator_metadata: Dict[str, Any]) -> List[str]:
        return [
            meta.get("indicator_code")
            for meta in indicator_metadata.values()
            if meta.get("indicator_code")
        ]

    @staticmethod
    def build_insert_select_from_base_delta_sql(
        dest_table: str,
        base_table: str,
        delta_table: Optional[str],
        target_metadata: Dict[str, Any],
        static_cols: list,
        inc_cols: list,
        etl_date: str,
    ) -> str:
        target_indicator_cols = AnalyzeDBPartitionManager._indicator_codes_in_metadata_order(
            target_metadata
        )
        static_set = set(static_cols)
        inc_set = set(inc_cols)

        insert_cols = ["target_id", *target_indicator_cols, "etl_date"]
        select_exprs = ["b.target_id"]

        for col in target_indicator_cols:
            if col in inc_set:
                select_exprs.append(f"d.{col}")
            elif col in static_set:
                select_exprs.append(f"b.{col}")
            else:
                select_exprs.append("NULL")

        select_exprs.append("b.etl_date")

        insert_clause = ", ".join(insert_cols)
        select_clause = ", ".join(select_exprs)
        join_clause = ""
        if delta_table and inc_cols:
            join_clause = (
                f"\\nLEFT JOIN {delta_table} d"
                f"\\n  ON b.target_id = d.target_id"
                f"\\n AND b.etl_date = d.etl_date"
            )

        return f"""
            INSERT INTO {dest_table} ({insert_clause})
            SELECT {select_clause}
            FROM {base_table} b{join_clause}
            WHERE b.etl_date = '{etl_date}'
        """

    @staticmethod
    def insert_select_from_base_delta(
        dest_table: str,
        base_table: str,
        delta_table: Optional[str],
        target_metadata: Dict[str, Any],
        static_cols: list,
        inc_cols: list,
        etl_date: str,
    ) -> int:
        sql = text(AnalyzeDBPartitionManager.build_insert_select_from_base_delta_sql(
            dest_table=dest_table,
            base_table=base_table,
            delta_table=delta_table,
            target_metadata=target_metadata,
            static_cols=static_cols,
            inc_cols=inc_cols,
            etl_date=etl_date,
        ))
        engine = AnalyzeDBConnector.get_engine()
        with engine.connect() as conn:
            result = conn.execute(sql)
            conn.commit()
            return result.rowcount
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/kyynor/Code/taosha_analyse_platform && pytest -c tests/backend/pytest.ini tests/backend/modules/wide_table_sync/test_delta_insert_select_sql.py -v`

Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/utils/analyze_db_utils.py tests/backend/modules/wide_table_sync/test_delta_insert_select_sql.py
git commit -m "feat: build wide table insert-select SQL"
```

---

### Task 3: Replace Copy/Update Incremental Sync Path

**Files:**
- Modify: `backend/services/fraudhunter/wide_table_service/sync_service.py`
- Modify: `tests/backend/modules/wide_table_sync/test_typed_pivot_sql.py`

**Interfaces:**
- Consumes:
  - `VersionDelta.removed_cols`
  - `_build_pivot_sql_inc(wide_table_name, indicator_metadata, etl_date, inc_codes)`
  - `AnalyzeDBPartitionManager.insert_select_from_base_delta(...)`
- Produces:
  - `_execute_delta_insert_select_sync(...) -> tuple[int, int]`

- [ ] **Step 1: Write a failing unit test for delta metadata filtering**

Append this test to `tests/backend/modules/wide_table_sync/test_typed_pivot_sql.py`:

```python
    def test_metadata_for_codes_keeps_only_requested_codes(self):
        metadata = {
            "1": {"indicator_code": "i_static", "data_type": "string"},
            "2": {"indicator_code": "i_changed", "data_type": "numeric"},
            "3": {"indicator_code": "i_new", "data_type": "string"},
        }

        filtered = _service()._metadata_for_codes(metadata, ["i_changed", "i_new"])

        assert set(filtered.keys()) == {"2", "3"}
        assert filtered["2"]["indicator_code"] == "i_changed"
        assert filtered["3"]["indicator_code"] == "i_new"
```

- [ ] **Step 2: Run tests to verify current pivot support still passes**

Run: `cd /Users/kyynor/Code/taosha_analyse_platform && pytest -c tests/backend/pytest.ini tests/backend/modules/wide_table_sync/test_typed_pivot_sql.py -v`

Expected: PASS. This confirms the existing incremental PIVOT building block remains usable before changing orchestration.

- [ ] **Step 3: Implement the new sync method**

In `backend/services/fraudhunter/wide_table_service/sync_service.py`, add this method after `_execute_data_sync`:

```python
    def _execute_delta_insert_select_sync(
        self,
        wide_table_name: str,
        target_metadata: dict,
        etl_date: date,
        pg_table_name: str,
        old_pg_table: str,
        static_cols: list,
        inc_cols: list,
    ) -> Tuple[int, int]:
        etl_date_str = etl_date.strftime('%Y-%m-%d')
        etl_date_suffix = etl_date.strftime('%Y%m%d')
        delta_table = None

        AnalyzeDBPartitionManager.create_wide_table(pg_table_name, target_metadata)
        AnalyzeDBPartitionManager.ensure_partition(pg_table_name, etl_date)

        try:
            if inc_cols:
                delta_table = f"_delta_{pg_table_name}_{etl_date_suffix}"
                inc_metadata = self._metadata_for_codes(target_metadata, inc_cols)
                AnalyzeDBPartitionManager.create_heap_table(delta_table, inc_metadata)

                pivot_sql = self._build_pivot_sql_inc(
                    wide_table_name, target_metadata, etl_date, inc_cols
                )
                refresh_sql = f"refresh table {self.source_table}"
                if self._use_pyspark:
                    self._execute_with_pyspark_to_pg(pivot_sql, delta_table, refresh_sql)
                else:
                    self._execute_with_jdbc_to_pg(pivot_sql, delta_table, etl_date, refresh_sql)

            row_count = AnalyzeDBPartitionManager.insert_select_from_base_delta(
                dest_table=pg_table_name,
                base_table=old_pg_table,
                delta_table=delta_table,
                target_metadata=target_metadata,
                static_cols=static_cols,
                inc_cols=inc_cols,
                etl_date=etl_date_str,
            )
            column_count = len(list(target_metadata.keys())) + 2
            return row_count, column_count
        finally:
            if delta_table:
                AnalyzeDBPartitionManager.drop_table(delta_table)
```

- [ ] **Step 4: Route sync_wide_table through the new method**

Replace this disabled branch:

```python
            if 1==2 and old_pg_table and inc_codes:
                ...
            else:
                logger.info("[骨架] 走全量同步路径（全量/无可用旧表/零变动）")
                row_count, column_count = self._execute_data_sync(
                    wide_table_name, indicator_metadata, etl_date, pg_table_name
                )
```

With:

```python
            delta = WideTableComparator.diff(effective_curr_md, indicator_metadata)
            changed, new_cols, static_cols = (
                delta.changed_cols,
                delta.new_cols,
                delta.static_cols,
            )
            inc_codes = delta.deferred_cols
            pg_table_name = f"{wide_table_name}_{version_hash[:8]}"

            if old_pg_table and delta.has_any_change:
                logger.info(
                    f"[增量] 走delta insert-select路径: {pg_table_name}, "
                    f"changed={len(changed)}, new={len(new_cols)}, "
                    f"removed={len(delta.removed_cols)}, static={len(static_cols)}"
                )
                row_count, column_count = self._execute_delta_insert_select_sync(
                    wide_table_name=wide_table_name,
                    target_metadata=indicator_metadata,
                    etl_date=etl_date,
                    pg_table_name=pg_table_name,
                    old_pg_table=old_pg_table,
                    static_cols=static_cols,
                    inc_cols=inc_codes,
                )
            else:
                logger.info("[全量] 走全量同步路径（无可用旧表或版本无变化）")
                row_count, column_count = self._execute_data_sync(
                    wide_table_name, indicator_metadata, etl_date, pg_table_name
                )
```

Remove the earlier call to `_diff_indicators()` in the same block so the method computes delta once.

- [ ] **Step 5: Keep `_copy_static_and_merge_incr()` present but unused**

Do not delete `_copy_static_and_merge_incr()` in this task. Leaving it present avoids a large deletion diff and keeps rollback simple. The new branch must not call it.

Verify with: `cd /Users/kyynor/Code/taosha_analyse_platform && rg "_copy_static_and_merge_incr\\(" backend/services/fraudhunter/wide_table_service/sync_service.py`

Expected: one result, the method definition only.

- [ ] **Step 6: Run focused tests**

Run:

```bash
cd /Users/kyynor/Code/taosha_analyse_platform
pytest -c tests/backend/pytest.ini tests/backend/modules/wide_table_sync/test_typed_pivot_sql.py tests/backend/modules/wide_table_sync/test_version_delta.py tests/backend/modules/wide_table_sync/test_delta_insert_select_sql.py -v
```

Expected: PASS for all focused tests.

- [ ] **Step 7: Commit**

```bash
git add backend/services/fraudhunter/wide_table_service/sync_service.py tests/backend/modules/wide_table_sync/test_typed_pivot_sql.py
git commit -m "feat: use delta insert-select wide table sync"
```

---

### Task 4: Add an Orchestration Unit Test for Branch Selection

**Files:**
- Create: `tests/backend/modules/wide_table_sync/test_delta_sync_branch.py`
- Modify: `backend/services/fraudhunter/wide_table_service/sync_service.py`

**Interfaces:**
- Consumes: `_execute_delta_insert_select_sync(...)`
- Produces: a testable branch decision using `_build_sync_delta(...) -> VersionDelta`

- [ ] **Step 1: Add a small wrapper for branch diff**

In `backend/services/fraudhunter/wide_table_service/sync_service.py`, add this method near `_diff_indicators()`:

```python
    def _build_sync_delta(self, current_metadata: dict, target_metadata: dict) -> VersionDelta:
        return WideTableComparator.diff(current_metadata, target_metadata)
```

This wrapper keeps branch-selection tests from importing `WideTableComparator` directly through service internals.

- [ ] **Step 2: Write the branch test**

Create `tests/backend/modules/wide_table_sync/test_delta_sync_branch.py`:

```python
import sys
from pathlib import Path

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

from domain.wide_table.version_delta import VersionDelta


def test_build_sync_delta_reports_removed_and_deferred_columns():
    from services.fraudhunter.wide_table_service.sync_service import WideTableSyncService

    service = WideTableSyncService.__new__(WideTableSyncService)
    current = {
        "1": {"version": 1, "indicator_code": "i_static"},
        "2": {"version": 1, "indicator_code": "i_changed"},
        "3": {"version": 1, "indicator_code": "i_removed"},
    }
    target = {
        "1": {"version": 1, "indicator_code": "i_static"},
        "2": {"version": 2, "indicator_code": "i_changed"},
        "4": {"version": 1, "indicator_code": "i_new"},
    }

    delta = service._build_sync_delta(current, target)

    assert isinstance(delta, VersionDelta)
    assert delta.static_cols == ["i_static"]
    assert delta.deferred_cols == ["i_changed", "i_new"]
    assert delta.removed_cols == ["i_removed"]
```

- [ ] **Step 3: Run the branch test**

Run: `cd /Users/kyynor/Code/taosha_analyse_platform && pytest -c tests/backend/pytest.ini tests/backend/modules/wide_table_sync/test_delta_sync_branch.py -v`

Expected: PASS.

- [ ] **Step 4: Run all wide-table tests**

Run: `cd /Users/kyynor/Code/taosha_analyse_platform && pytest -c tests/backend/pytest.ini tests/backend/modules/wide_table_sync -v`

Expected: PASS or only pre-existing skipped integration placeholders remain skipped.

- [ ] **Step 5: Commit**

```bash
git add backend/services/fraudhunter/wide_table_service/sync_service.py tests/backend/modules/wide_table_sync/test_delta_sync_branch.py
git commit -m "test: cover delta sync branch metadata"
```

---

### Task 5: Manual Integration Verification

**Files:**
- Modify: no source files unless verification exposes a defect.
- Test: existing DS or local backend environment with a small real PG dataset.

**Interfaces:**
- Consumes: completed Tasks 1-4.
- Produces: verified runtime behavior for one changed indicator over one `etl_date`.

- [ ] **Step 1: Choose a safe test date and wide table**

Use one date where a current ready snapshot exists. Example values:

```text
wide_table_name = dep_acct_wide_table
etl_date = 2026-07-06
```

Record the current version hash and target version hash from `fraudhunter_wide_table_version`.

- [ ] **Step 2: Run one-date sync through Python**

Run:

```bash
cd /Users/kyynor/Code/taosha_analyse_platform/backend
uv run python - <<'PY'
from datetime import date
from services.fraudhunter.wide_table_service.sync_service import WideTableSyncService

service = WideTableSyncService()
result = service.sync_multi_dates(
    wide_table_name="dep_acct_wide_table",
    lookback_days=1,
)
print(result)
PY
```

Expected: result has `synced >= 1` or `skipped_ready >= 1`. Logs include `[增量] 走delta insert-select路径` when a target version with a reusable base partition exists.

- [ ] **Step 3: Verify PG table and snapshot**

Run a PG query through the app DB utilities:

```bash
cd /Users/kyynor/Code/taosha_analyse_platform/backend
uv run python - <<'PY'
from utils.analyze_db_utils import AnalyzeDBConnector

df = AnalyzeDBConnector.execute_sql(
    "select table_name from information_schema.tables where table_schema='public' and table_name like '_delta_%'",
    fetch_df=True,
)
print(df)
PY
```

Expected: no leftover `_delta_%` table for the completed date.

- [ ] **Step 4: Verify changed nulls do not fall back**

For one changed indicator that has a known null or empty result after rerun, query the new version partition and old version partition by the same `target_id`.

Expected: new table changed column reflects the delta value. If delta value is null, new table value is null and does not reuse the old table value.

- [ ] **Step 5: Commit verification fixes if needed**

If verification required a code fix:

```bash
git add backend/services/fraudhunter/wide_table_service/sync_service.py backend/utils/analyze_db_utils.py tests/backend/modules/wide_table_sync
git commit -m "fix: stabilize delta insert-select sync"
```

If no fix was required, do not create an empty commit.

---

## Self-Review

- Spec coverage: Tasks cover removed indicators, reusable old partition path, delta PIVOT, PG insert-select, fallback to full sync, snapshot compatibility, and no `COALESCE` on keys or changed values.
- Placeholder scan: Plan contains concrete paths, commands, expected outputs, function signatures, and code snippets.
- Type consistency: `VersionDelta.removed_cols`, `VersionDelta.deferred_cols`, `_execute_delta_insert_select_sync`, and `AnalyzeDBPartitionManager.insert_select_from_base_delta` are consistently named across tasks.
