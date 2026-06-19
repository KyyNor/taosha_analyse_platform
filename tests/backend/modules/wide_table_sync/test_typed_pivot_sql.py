import importlib.util
import sys
import types
from datetime import date
from pathlib import Path

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))


def _load_sync_service_with_stubs():
    services_module = types.ModuleType("services")
    fraudhunter_module = types.ModuleType("services.fraudhunter")
    wide_table_service_module = types.ModuleType("services.fraudhunter.wide_table_service")

    models_module = types.ModuleType("models")
    models_fraudhunter_module = types.ModuleType("models.fraudhunter")
    wide_table_module = types.ModuleType("models.fraudhunter.wide_table")
    wide_table_module.FraudHunterWideTableVersion = object
    wide_table_module.FraudHunterWideTableSnapshot = object

    db_base_module = types.ModuleType("models.db_base")
    db_base_module.get_db_session = lambda: None

    version_manager_module = types.ModuleType(
        "services.fraudhunter.wide_table_service.version_manager"
    )
    version_manager_module.WideTableVersionManager = object

    logger_module = types.ModuleType("utils.logger")
    logger_module.logger = types.SimpleNamespace(
        debug=lambda *args, **kwargs: None,
        info=lambda *args, **kwargs: None,
        warning=lambda *args, **kwargs: None,
        error=lambda *args, **kwargs: None,
    )

    config_module = types.ModuleType("utils.config")
    config_module.settings = types.SimpleNamespace(
        fraudhunter_wide_table_source_table="source_indicator_vertical",
        pyspark_enabled=False,
        fraudhunter_realtime_writer_batch_insert_size=1000,
    )

    analyze_db_utils_module = types.ModuleType("utils.analyze_db_utils")
    analyze_db_utils_module.AnalyzeDBConnector = object
    analyze_db_utils_module.AnalyzeDBPartitionManager = object

    domain_module = types.ModuleType("domain")
    domain_wide_table_module = types.ModuleType("domain.wide_table")
    version_delta_module = types.ModuleType("domain.wide_table.version_delta")
    version_delta_module.WideTableComparator = object

    numeric_module_path = (
        _backend_root
        / "services"
        / "fraudhunter"
        / "wide_table_service"
        / "numeric_type_utils.py"
    )
    numeric_spec = importlib.util.spec_from_file_location(
        "services.fraudhunter.wide_table_service.numeric_type_utils",
        numeric_module_path,
    )
    numeric_module = importlib.util.module_from_spec(numeric_spec)
    sys.modules[numeric_spec.name] = numeric_module
    numeric_spec.loader.exec_module(numeric_module)

    for name, module in {
        "services": services_module,
        "services.fraudhunter": fraudhunter_module,
        "services.fraudhunter.wide_table_service": wide_table_service_module,
        "models": models_module,
        "models.fraudhunter": models_fraudhunter_module,
        "models.fraudhunter.wide_table": wide_table_module,
        "models.db_base": db_base_module,
        "services.fraudhunter.wide_table_service.version_manager": version_manager_module,
        "utils.logger": logger_module,
        "utils.config": config_module,
        "utils.analyze_db_utils": analyze_db_utils_module,
        "domain": domain_module,
        "domain.wide_table": domain_wide_table_module,
        "domain.wide_table.version_delta": version_delta_module,
    }.items():
        sys.modules[name] = module

    module_path = (
        _backend_root
        / "services"
        / "fraudhunter"
        / "wide_table_service"
        / "sync_service.py"
    )
    spec = importlib.util.spec_from_file_location(
        "services.fraudhunter.wide_table_service.sync_service",
        module_path,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


WideTableSyncService = _load_sync_service_with_stubs().WideTableSyncService


def _service():
    service = WideTableSyncService.__new__(WideTableSyncService)
    service.source_table = "source_indicator_vertical"
    return service


class TestTypedPivotSql:
    def test_full_pivot_casts_numeric_columns_and_keeps_text_columns(self):
        metadata = {
            "1": {"indicator_code": "i_amt", "data_type": "numeric"},
            "2": {"indicator_code": "i_name", "data_type": "string"},
        }

        sql = _service()._build_pivot_sql(
            "dep_acct_wide_table",
            metadata,
            date(2026, 6, 18),
        )

        assert "FROM (" in sql
        assert "PIVOT" in sql
        assert "target_id,\n        indicator_id,\n        indicator_value" in sql
        assert "CASE WHEN i_amt IS NULL" in sql
        assert "RLIKE" in sql
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
        assert "RLIKE" in sql
        assert "CAST(TRIM(CAST(i_amt AS STRING)) AS DOUBLE)" in sql
        assert "i_name" not in sql
