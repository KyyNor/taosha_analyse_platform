import importlib.util
import asyncio
import sys
import types
from pathlib import Path

import pandas as pd

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

_module_path = (
    _backend_root
    / "services"
    / "fraudhunter"
    / "wide_table_service"
    / "numeric_type_utils.py"
)
_spec = importlib.util.spec_from_file_location("numeric_type_utils", _module_path)
numeric_type_utils = importlib.util.module_from_spec(_spec)
sys.modules["numeric_type_utils"] = numeric_type_utils
_spec.loader.exec_module(numeric_type_utils)

NumericConversionStats = numeric_type_utils.NumericConversionStats
WideTableNumericTypeHelper = numeric_type_utils.WideTableNumericTypeHelper


def _load_analyze_db_utils_with_stubs(monkeypatch):
    services_module = types.ModuleType("services")
    fraudhunter_module = types.ModuleType("services.fraudhunter")
    wide_table_service_module = types.ModuleType("services.fraudhunter.wide_table_service")

    config_module = types.ModuleType("utils.config")
    config_module.settings = types.SimpleNamespace(
        fraudhunter_analyze_db={
            "db_type": "postgresql",
            "postgresql": {},
        }
    )

    db_base_module = types.ModuleType("models.db_base")
    db_base_module.get_db_session = lambda: None

    system_config_module = types.ModuleType("services.fraudhunter.system_config_service")
    system_config_module.SystemConfigManager = object

    for name, module in {
        "services": services_module,
        "services.fraudhunter": fraudhunter_module,
        "services.fraudhunter.wide_table_service": wide_table_service_module,
        "services.fraudhunter.wide_table_service.numeric_type_utils": numeric_type_utils,
        "utils.config": config_module,
        "models.db_base": db_base_module,
        "services.fraudhunter.system_config_service": system_config_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    module_path = _backend_root / "utils" / "analyze_db_utils.py"
    spec = importlib.util.spec_from_file_location("analyze_db_utils_for_test", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["analyze_db_utils_for_test"] = module
    spec.loader.exec_module(module)
    return module


class TestWideTableNumericTypeHelper:
    def test_is_numeric_meta_true_for_numeric(self):
        meta = {"indicator_code": "i_amt", "data_type": "numeric"}
        assert WideTableNumericTypeHelper.is_numeric_meta(meta) is True

    def test_is_numeric_meta_true_for_uppercase_numeric(self):
        meta = {"indicator_code": "i_amt", "data_type": "NUMERIC"}
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

    def test_numeric_indicator_codes_returns_only_numeric_codes(self):
        metadata = {
            "1": {"indicator_code": "i_amt", "data_type": "numeric"},
            "2": {"indicator_code": "i_name", "data_type": "string"},
            "3": {"indicator_code": "i_rate", "data_type": "NUMERIC"},
            "4": {"data_type": "numeric"},
        }
        assert WideTableNumericTypeHelper.numeric_indicator_codes(metadata) == ["i_amt", "i_rate"]

    def test_spark_numeric_safe_cast_expression_handles_blank_and_invalid_values(self):
        expr = WideTableNumericTypeHelper.spark_select_expression(
            {"indicator_code": "i_amt", "data_type": "numeric"}
        )
        assert "CASE" in expr
        assert "TRIM(CAST(i_amt AS STRING)) = ''" in expr
        assert "RLIKE" in expr
        assert "CAST(TRIM(CAST(i_amt AS STRING)) AS DOUBLE)" in expr
        assert "ELSE CAST(NULL AS DOUBLE)" in expr
        assert "AS i_amt" in expr

    def test_spark_non_numeric_expression_passes_column_through(self):
        expr = WideTableNumericTypeHelper.spark_select_expression(
            {"indicator_code": "i_name", "data_type": "string"}
        )
        assert expr == "i_name"

    def test_spark_select_expressions_mixes_numeric_and_text(self):
        metadata = {
            "1": {"indicator_code": "i_amt", "data_type": "numeric"},
            "2": {"indicator_code": "i_name", "data_type": "string"},
        }
        expressions = WideTableNumericTypeHelper.spark_select_expressions(metadata)
        assert expressions[0].endswith("AS i_amt")
        assert expressions[1] == "i_name"

    def test_convert_numeric_dataframe_columns_turns_blank_invalid_to_null(self):
        df = pd.DataFrame(
            {
                "target_id": ["a", "b", "c", "d"],
                "i_amt": ["12.5", "", "  ", "not-a-number"],
                "i_name": ["x", "y", "z", "w"],
            }
        )
        metadata = {
            "1": {"indicator_code": "i_amt", "data_type": "numeric"},
            "2": {"indicator_code": "i_name", "data_type": "string"},
        }

        converted, stats = WideTableNumericTypeHelper.convert_numeric_dataframe_columns(df, metadata)

        assert converted is not df
        assert df["i_amt"].tolist() == ["12.5", "", "  ", "not-a-number"]
        assert converted["i_amt"].dtype == "float64"
        assert converted["i_amt"].tolist()[0] == 12.5
        assert pd.isna(converted["i_amt"].tolist()[1])
        assert pd.isna(converted["i_amt"].tolist()[2])
        assert pd.isna(converted["i_amt"].tolist()[3])
        assert converted["i_name"].tolist() == ["x", "y", "z", "w"]
        assert stats == [
            NumericConversionStats(indicator_code="i_amt", blank_count=2, invalid_count=1)
        ]

    def test_convert_realtime_numeric_dataframe_columns_counts_blank_not_invalid(self):
        df = pd.DataFrame(
            {
                "target_id": ["a", "b"],
                "i_amt": ["100.25", ""],
            }
        )
        metadata = {
            "1": {"indicator_code": "i_amt", "data_type": "numeric"},
        }

        converted, stats = WideTableNumericTypeHelper.convert_numeric_dataframe_columns(df, metadata)

        assert converted["i_amt"].tolist()[0] == 100.25
        assert pd.isna(converted["i_amt"].tolist()[1])
        assert stats == [
            NumericConversionStats(indicator_code="i_amt", blank_count=1, invalid_count=0)
        ]

    def test_realtime_indicator_job_uses_numeric_conversion_before_copy(self):
        job_source = (
            _backend_root
            / "services"
            / "scheduler"
            / "jobs"
            / "realtime_indicator_job.py"
        ).read_text()

        assert (
            "from services.fraudhunter.wide_table_service.numeric_type_utils "
            "import WideTableNumericTypeHelper"
        ) in job_source
        etl_pos = job_source.index("final_result['etl_date'] = today")
        run_time_pos = job_source.index("final_result['run_time'] = half_hour_slot")
        convert_pos = job_source.index(
            "WideTableNumericTypeHelper.convert_numeric_dataframe_columns("
        )
        copy_pos = job_source.index("AnalyzeDBConnector.batch_insert_copy(")

        assert etl_pos < convert_pos
        assert run_time_pos < convert_pos
        assert convert_pos < copy_pos
        assert "stats.blank_count" in job_source
        assert "stats.invalid_count" in job_source

    def test_convert_numeric_dataframe_columns_counts_null_blank_and_invalid(self):
        df = pd.DataFrame(
            {
                "i_amt": [None, "1", "1e3", ".5", "-2.25", "bad"],
            }
        )
        metadata = {
            "1": {"indicator_code": "i_amt", "data_type": "numeric"},
        }

        converted, stats = WideTableNumericTypeHelper.convert_numeric_dataframe_columns(df, metadata)

        assert converted["i_amt"].tolist()[1:5] == [1.0, 1000.0, 0.5, -2.25]
        assert pd.isna(converted["i_amt"].tolist()[0])
        assert pd.isna(converted["i_amt"].tolist()[5])
        assert stats == [
            NumericConversionStats(indicator_code="i_amt", blank_count=1, invalid_count=1)
        ]

    def test_convert_numeric_dataframe_columns_rejects_values_outside_spark_regex(self):
        df = pd.DataFrame(
            {
                "i_amt": ["inf", "Infinity", "+1", "-1", "1e2"],
            }
        )
        metadata = {
            "1": {"indicator_code": "i_amt", "data_type": "numeric"},
        }

        converted, stats = WideTableNumericTypeHelper.convert_numeric_dataframe_columns(df, metadata)

        assert pd.isna(converted["i_amt"].tolist()[0])
        assert pd.isna(converted["i_amt"].tolist()[1])
        assert pd.isna(converted["i_amt"].tolist()[2])
        assert converted["i_amt"].tolist()[3:] == [-1.0, 100.0]
        assert stats == [
            NumericConversionStats(indicator_code="i_amt", blank_count=0, invalid_count=3)
        ]

    def test_numeric_conversion_stats_equality(self):
        assert NumericConversionStats("i_amt", 1, 2) == NumericConversionStats("i_amt", 1, 2)
        assert NumericConversionStats("i_amt", 1, 2) != NumericConversionStats("i_amt", 2, 1)

    def test_numeric_conversion_stats_serializes_with_dict(self):
        stats = [NumericConversionStats(indicator_code="i_amt", blank_count=1, invalid_count=2)]

        assert [stat.__dict__ for stat in stats] == [
            {"indicator_code": "i_amt", "blank_count": 1, "invalid_count": 2}
        ]


class TestAnalyzeDBPartitionManagerNumericColumns:
    def test_resolve_indicator_column_def_uses_double_precision_for_numeric(self, monkeypatch):
        module = _load_analyze_db_utils_with_stubs(monkeypatch)

        result = module.AnalyzeDBPartitionManager.resolve_indicator_column_def(
            {"indicator_code": "i_amt", "data_type": "numeric"},
            [],
        )

        assert result == ("i_amt", "DOUBLE PRECISION")

    def test_resolve_indicator_column_def_keeps_long_text_for_nonnumeric(self, monkeypatch):
        module = _load_analyze_db_utils_with_stubs(monkeypatch)

        result = module.AnalyzeDBPartitionManager.resolve_indicator_column_def(
            {"indicator_code": "i_desc", "data_type": "string"},
            ["i_desc"],
        )

        assert result == ("i_desc", "text")

    def test_resolve_indicator_column_def_requires_indicator_code(self, monkeypatch):
        module = _load_analyze_db_utils_with_stubs(monkeypatch)

        try:
            module.AnalyzeDBPartitionManager.resolve_indicator_column_def(
                {"data_type": "numeric"},
                [],
            )
        except ValueError as exc:
            assert str(exc) == "indicator_code is required"
        else:
            raise AssertionError("Expected ValueError")

    def test_create_wide_table_requires_indicator_code(self, monkeypatch):
        module = _load_analyze_db_utils_with_stubs(monkeypatch)

        try:
            module.AnalyzeDBPartitionManager.create_wide_table(
                "wide_table",
                {"1": {"data_type": "numeric"}},
            )
        except ValueError as exc:
            assert str(exc) == "indicator_code is required"
        else:
            raise AssertionError("Expected ValueError")

    def test_create_heap_table_requires_indicator_code(self, monkeypatch):
        module = _load_analyze_db_utils_with_stubs(monkeypatch)

        try:
            module.AnalyzeDBPartitionManager.create_heap_table(
                "heap_table",
                {"1": {"data_type": "numeric"}},
            )
        except ValueError as exc:
            assert str(exc) == "indicator_code is required"
        else:
            raise AssertionError("Expected ValueError")


def _load_version_manager_with_stubs(monkeypatch):
    class DummyTask:
        id = "id"

    sqlalchemy_module = types.ModuleType("sqlalchemy")
    sqlalchemy_module.and_ = lambda *args: args
    sqlalchemy_module.func = object()
    sqlalchemy_orm_module = types.ModuleType("sqlalchemy.orm")
    sqlalchemy_orm_module.Session = object

    indicator_module = types.ModuleType("models.fraudhunter.indicator")
    indicator_module.FraudHunterIndicatorDefinition = object
    indicator_module.FraudHunterIndicatorTask = DummyTask

    wide_table_module = types.ModuleType("models.fraudhunter.wide_table")
    wide_table_module.FraudHunterWideTableVersion = object
    wide_table_module.FraudHunterWideTableSnapshot = object
    wide_table_module.FraudHunterIndicatorRunProgress = object

    logger_module = types.ModuleType("utils.logger")
    logger_module.logger = types.SimpleNamespace(
        info=lambda *args, **kwargs: None,
        debug=lambda *args, **kwargs: None,
        warning=lambda *args, **kwargs: None,
        error=lambda *args, **kwargs: None,
    )

    analyze_db_module = types.ModuleType("utils.analyze_db_utils")
    analyze_db_module.AnalyzeDBPartitionManager = object

    for name, module in {
        "sqlalchemy": sqlalchemy_module,
        "sqlalchemy.orm": sqlalchemy_orm_module,
        "models.fraudhunter.indicator": indicator_module,
        "models.fraudhunter.wide_table": wide_table_module,
        "utils.logger": logger_module,
        "utils.analyze_db_utils": analyze_db_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    module_path = (
        _backend_root
        / "services"
        / "fraudhunter"
        / "wide_table_service"
        / "version_manager.py"
    )
    spec = importlib.util.spec_from_file_location("version_manager_for_test", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["version_manager_for_test"] = module
    spec.loader.exec_module(module)
    return module


class TestWideTableVersionManagerNumericMetadata:
    def test_generate_version_hash_includes_indicator_data_type(self, monkeypatch):
        module = _load_version_manager_with_stubs(monkeypatch)

        class Query:
            def filter(self, *args):
                return self

            def first(self):
                return types.SimpleNamespace(current_version=7)

        manager = module.WideTableVersionManager.__new__(module.WideTableVersionManager)
        manager.db = types.SimpleNamespace(query=lambda _model: Query())
        indicator = types.SimpleNamespace(
            id=1,
            current_version=3,
            indicator_task_id=2,
            indicator_code="i_amt",
            indicator_name="金额",
            indicator_type="offline",
            object_type="dep_acct_no",
            data_type="numeric",
        )

        _version_hash, indicator_metadata = manager.generate_version_hash([indicator])

        assert indicator_metadata[1]["data_type"] == "numeric"


def _load_indicator_executor(monkeypatch):
    class DummyColumn:
        def __eq__(self, _other):
            return True

        def in_(self, _values):
            return True

    class DummyTask:
        id = DummyColumn()

    class DummyExecution:
        execution_id = DummyColumn()

    class DummyIndicator:
        id = DummyColumn()

    sqlalchemy_orm_module = types.ModuleType("sqlalchemy.orm")
    sqlalchemy_orm_module.Session = object

    models_module = types.ModuleType("models")
    fraudhunter_module = types.ModuleType("models.fraudhunter")
    indicator_module = types.ModuleType("models.fraudhunter.indicator")
    indicator_module.FraudHunterIndicatorTask = DummyTask
    indicator_module.FraudHunterIndicatorDefinition = DummyIndicator

    dry_run_model_module = types.ModuleType("models.fraudhunter.dry_run_task")
    dry_run_model_module.FraudHunterDryRunExecution = DummyExecution

    schemas_module = types.ModuleType("schemas")
    schemas_fraudhunter_module = types.ModuleType("schemas.fraudhunter")
    schemas_indicator_module = types.ModuleType("schemas.fraudhunter.indicator")
    schemas_indicator_module.IndicatorTaskCreate = object

    services_module = types.ModuleType("services")
    services_fraudhunter_module = types.ModuleType("services.fraudhunter")
    wide_table_service_module = types.ModuleType("services.fraudhunter.wide_table_service")

    logger_module = types.ModuleType("utils.logger")
    logger_module.logger = types.SimpleNamespace(
        info=lambda *args, **kwargs: None,
        debug=lambda *args, **kwargs: None,
        warning=lambda *args, **kwargs: None,
        error=lambda *args, **kwargs: None,
    )

    spark_utils_module = types.ModuleType("utils.spark_utils")
    spark_utils_module.spark_utils = types.SimpleNamespace(query_sql=lambda _sql: [])

    db_base_module = types.ModuleType("models.db_base")
    db_base_module.SessionLocal = lambda: None

    for name, module in {
        "sqlalchemy.orm": sqlalchemy_orm_module,
        "models": models_module,
        "models.fraudhunter": fraudhunter_module,
        "models.fraudhunter.indicator": indicator_module,
        "models.fraudhunter.dry_run_task": dry_run_model_module,
        "schemas": schemas_module,
        "schemas.fraudhunter": schemas_fraudhunter_module,
        "schemas.fraudhunter.indicator": schemas_indicator_module,
        "services": services_module,
        "services.fraudhunter": services_fraudhunter_module,
        "services.fraudhunter.wide_table_service": wide_table_service_module,
        "services.fraudhunter.wide_table_service.numeric_type_utils": numeric_type_utils,
        "utils.logger": logger_module,
        "utils.spark_utils": spark_utils_module,
        "models.db_base": db_base_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    module_path = (
        _backend_root
        / "services"
        / "fraudhunter"
        / "dry_run_task_service"
        / "indicator_executor.py"
    )
    spec = importlib.util.spec_from_file_location("indicator_executor_for_test", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["indicator_executor_for_test"] = module
    spec.loader.exec_module(module)
    return module


class TestIndicatorExecutorNumericConversionStats:
    class FakeQuery:
        def __init__(self, db, model):
            self.db = db
            self.model = model

        def filter(self, *args):
            return self

        def first(self):
            if self.model is self.db.module.FraudHunterIndicatorTask:
                return self.db.task
            if self.model is self.db.module.FraudHunterDryRunExecution:
                return self.db.execution
            raise AssertionError(f"unexpected first() model: {self.model}")

        def all(self):
            if self.model is self.db.module.FraudHunterIndicatorDefinition:
                if self.db.after_spark and self.db.fail_indicator_query_after_spark:
                    raise AssertionError("indicator metadata must be fetched before Spark execution")
                return self.db.indicators
            raise AssertionError(f"unexpected all() model: {self.model}")

    class FakeDb:
        def __init__(self, module, task, execution, indicators):
            self.module = module
            self.task = task
            self.execution = execution
            self.indicators = indicators
            self.after_spark = False
            self.fail_indicator_query_after_spark = False
            self.commits = 0

        def query(self, model):
            return TestIndicatorExecutorNumericConversionStats.FakeQuery(self, model)

        def flush(self):
            pass

        def commit(self):
            self.commits += 1

    def _make_executor_and_db(self, monkeypatch):
        module = _load_indicator_executor(monkeypatch)
        execution = types.SimpleNamespace(
            execution_id="exec-1",
            etl_date=None,
            version=None,
            parameters=None,
            rows_processed=None,
            rows_output=None,
            duration_seconds=None,
            log_content=None,
            error_message=None,
        )
        indicators = [
            types.SimpleNamespace(id=1, indicator_code="i_amt", data_type="numeric"),
            types.SimpleNamespace(id=2, indicator_code="i_name", data_type="text"),
        ]
        task = types.SimpleNamespace(
            id=10,
            task_code="task_amt",
            logic_content="select * from source",
            current_version=1,
            indicators=indicators,
        )
        db = self.FakeDb(module, task, execution, indicators)

        class FakeExecutor(module.IndicatorExecutor):
            async def _spark_execution(self, sql, etl_date, sample_size, indicator_codes=None):
                db.after_spark = True
                return {
                    "rows_processed": 3,
                    "rows_output": 3,
                    "duration_seconds": 0.1,
                    "sample_result": [
                        {"target_id": "a", "etl_date": etl_date, "i_amt": "12.5", "i_name": "ok"},
                        {"target_id": "b", "etl_date": etl_date, "i_amt": "", "i_name": "blank"},
                        {"target_id": "c", "etl_date": etl_date, "i_amt": "bad", "i_name": "invalid"},
                    ],
                    "log_content": "ok",
                }

        return FakeExecutor(), db

    def test_execute_dry_run_reports_numeric_stats_from_task_indicators_without_indicator_ids(self, monkeypatch):
        executor, db = self._make_executor_and_db(monkeypatch)

        result = asyncio.run(
            executor.execute_dry_run(
                db=db,
                execution_id="exec-1",
                task_id=10,
                etl_date="2026-06-19",
                sample_size=10,
            )
        )

        assert result["numeric_conversion_stats"] == [
            {"indicator_code": "i_amt", "blank_count": 1, "invalid_count": 1}
        ]
        assert result["sample_result"][1]["i_amt"] == ""
        assert result["sample_result"][2]["i_amt"] == "bad"

    def test_execute_dry_run_prefetches_numeric_metadata_before_spark(self, monkeypatch):
        executor, db = self._make_executor_and_db(monkeypatch)
        db.fail_indicator_query_after_spark = True

        result = asyncio.run(
            executor.execute_dry_run(
                db=db,
                execution_id="exec-1",
                task_id=10,
                etl_date="2026-06-19",
                sample_size=10,
                indicator_ids=[1, 2],
            )
        )

        assert result["numeric_conversion_stats"][0]["indicator_code"] == "i_amt"
