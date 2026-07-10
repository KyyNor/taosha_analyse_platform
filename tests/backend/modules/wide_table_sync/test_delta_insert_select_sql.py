import sys
import types
import importlib.util
from pathlib import Path

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))


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

    numeric_type_utils_module = types.ModuleType(
        "services.fraudhunter.wide_table_service.numeric_type_utils"
    )
    numeric_type_utils_module.WideTableNumericTypeHelper = object

    for name, module in {
        "services": services_module,
        "services.fraudhunter": fraudhunter_module,
        "services.fraudhunter.wide_table_service": wide_table_service_module,
        "services.fraudhunter.wide_table_service.numeric_type_utils": numeric_type_utils_module,
        "utils.config": config_module,
        "models.db_base": db_base_module,
        "services.fraudhunter.system_config_service": system_config_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    module_path = _backend_root / "utils" / "analyze_db_utils.py"
    spec = importlib.util.spec_from_file_location("analyze_db_utils_for_delta_test", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["analyze_db_utils_for_delta_test"] = module
    spec.loader.exec_module(module)
    return module


class TestDeltaInsertSelectSql:
    def test_build_insert_select_uses_left_join_and_base_keys(self, monkeypatch):
        manager = _load_analyze_db_utils_with_stubs(monkeypatch).AnalyzeDBPartitionManager
        metadata = {
            "1": {"indicator_code": "i_static"},
            "2": {"indicator_code": "i_changed"},
            "3": {"indicator_code": "i_new"},
        }

        sql = manager.build_insert_select_from_base_delta_sql(
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

    def test_build_insert_select_without_delta_for_removed_only_change(self, monkeypatch):
        manager = _load_analyze_db_utils_with_stubs(monkeypatch).AnalyzeDBPartitionManager
        metadata = {
            "1": {"indicator_code": "i_static"},
        }

        sql = manager.build_insert_select_from_base_delta_sql(
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
