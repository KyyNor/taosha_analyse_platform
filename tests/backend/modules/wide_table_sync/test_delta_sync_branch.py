import importlib.util
import sys
import types
from datetime import date
from pathlib import Path

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

from domain.wide_table.version_delta import VersionDelta

_version_delta_module = sys.modules[VersionDelta.__module__]


def _load_sync_service_with_stubs(monkeypatch):
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
    monkeypatch.setitem(sys.modules, numeric_spec.name, numeric_module)
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
        "domain.wide_table.version_delta": _version_delta_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

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
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module.WideTableSyncService


def test_build_sync_delta_reports_removed_and_deferred_columns(monkeypatch):
    WideTableSyncService = _load_sync_service_with_stubs(monkeypatch)
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


def test_sync_wide_table_skips_unchanged_metadata_with_reusable_base(monkeypatch):
    WideTableSyncService = _load_sync_service_with_stubs(monkeypatch)
    service = WideTableSyncService.__new__(WideTableSyncService)

    target_metadata = {
        "1": {"version": 1, "indicator_code": "i_same"},
    }
    calls = {
        "full_sync": 0,
        "delta_sync": 0,
        "mark_ready": 0,
    }

    monkeypatch.setattr(service, "_check_version_ready", lambda *args: True)
    monkeypatch.setattr(service, "_get_existing_snapshot", lambda *args: None)
    monkeypatch.setattr(
        service,
        "_find_copy_source",
        lambda *args: ("dep_acct_wide_table_base_20260102", target_metadata),
    )
    monkeypatch.setattr(service, "_create_generating_snapshot", lambda *args: 123)

    def record_full_sync(*args, **kwargs):
        calls["full_sync"] += 1
        return (10, 3)

    def record_delta_sync(*args, **kwargs):
        calls["delta_sync"] += 1
        return (10, 3)

    def record_mark_ready(*args, **kwargs):
        calls["mark_ready"] += 1

    monkeypatch.setattr(service, "_execute_data_sync", record_full_sync)
    monkeypatch.setattr(service, "_execute_delta_insert_select_sync", record_delta_sync)
    monkeypatch.setattr(service, "_update_snapshot_ready", record_mark_ready)
    monkeypatch.setattr(service, "_update_snapshot_failed", lambda *args: None)

    result = service.sync_wide_table(
        target_version_id=1,
        wide_table_name="dep_acct_wide_table",
        version_hash="abcdef1234567890",
        indicator_metadata=target_metadata,
        etl_date=date(2026, 1, 2),
        copy_candidates=[{"version_hash": "basehash12345678"}],
    )

    assert result["status"] == "skipped"
    assert result["skip_reason"] == "version_unchanged_with_reusable_base"
    assert result["is_new_sync"] is False
    assert calls == {
        "full_sync": 0,
        "delta_sync": 0,
        "mark_ready": 0,
    }


def test_find_copy_source_logs_when_no_candidates(monkeypatch):
    WideTableSyncService = _load_sync_service_with_stubs(monkeypatch)
    service = WideTableSyncService.__new__(WideTableSyncService)
    module = sys.modules[WideTableSyncService.__module__]
    warnings = []
    module.logger.warning = warnings.append

    result = service._find_copy_source(
        "dep_acct_wide_table",
        date(2026, 8, 11),
        [],
    )

    assert result == (None, None)
    assert any("reason=no_copy_candidates" in message for message in warnings)
    assert any("首次同步" in message for message in warnings)


def test_find_copy_source_logs_each_rejection_reason(monkeypatch):
    WideTableSyncService = _load_sync_service_with_stubs(monkeypatch)
    service = WideTableSyncService.__new__(WideTableSyncService)
    module = sys.modules[WideTableSyncService.__module__]
    info_logs = []
    warning_logs = []
    module.logger.info = info_logs.append
    module.logger.warning = warning_logs.append

    class FakePartitionManager:
        @staticmethod
        def table_exists(table_name):
            return "missing1" not in table_name

        @staticmethod
        def count_partition_rows(table_name):
            if "empty222" in table_name:
                return 0
            return -1

    sys.modules[
        "utils.analyze_db_utils"
    ].AnalyzeDBPartitionManager = FakePartitionManager

    result = service._find_copy_source(
        "cust_wide_table",
        date(2026, 8, 11),
        [
            {"version_hash": None, "status": "history"},
            {"version_hash": "missing1abcdef", "status": "history"},
            {"version_hash": "empty222abcdef", "status": "history"},
            {"version_hash": "failed33abcdef", "status": "current"},
        ],
    )

    assert result == (None, None)
    combined_info = "\n".join(info_logs)
    combined_warning = "\n".join(warning_logs)
    assert "reason=missing_version_hash" in combined_info
    assert "reason=table_missing_or_check_failed" in combined_info
    assert "reason=empty_partition" in combined_info
    assert "reason=row_count_failed" in combined_info
    assert "reason=no_usable_old_partition" in combined_warning
    assert "checked=4" in combined_warning
    assert "missing_version_hash=1" in combined_warning
    assert "table_missing_or_check_failed=1" in combined_warning
    assert "empty_partition=1" in combined_warning
    assert "row_count_failed=1" in combined_warning


def test_find_copy_source_logs_selected_partition(monkeypatch):
    WideTableSyncService = _load_sync_service_with_stubs(monkeypatch)
    service = WideTableSyncService.__new__(WideTableSyncService)
    module = sys.modules[WideTableSyncService.__module__]
    info_logs = []
    module.logger.info = info_logs.append

    class FakePartitionManager:
        @staticmethod
        def table_exists(table_name):
            return True

        @staticmethod
        def count_partition_rows(table_name):
            return 42

    sys.modules[
        "utils.analyze_db_utils"
    ].AnalyzeDBPartitionManager = FakePartitionManager
    metadata = {"1": {"version": 1, "indicator_code": "i_balance"}}

    result = service._find_copy_source(
        "loan_acct_wide_table",
        date(2026, 8, 11),
        [
            {
                "version_hash": "usable12abcdef",
                "status": "current",
                "indicator_metadata": metadata,
            }
        ],
    )

    assert result == ("loan_acct_wide_table_usable12_20260811", metadata)
    selected_log = "\n".join(info_logs)
    assert "选中可复用旧分区" in selected_log
    assert "row_count=42" in selected_log
    assert "indicators=1" in selected_log
