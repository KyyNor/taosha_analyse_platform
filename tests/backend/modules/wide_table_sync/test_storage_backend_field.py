"""
阶段1：元数据与配置基础 —— storage_backend 字段与 offline_store 配置项

对应 docs/fraudhunter_offline_dual_store_plan.md 阶段1：
- FraudHunterWideTableSnapshot 模型新增 storage_backend 字段（默认 postgresql）；
- 配置新增 offline_store / duckdb.* 配置项，缺省值不改变任何现有行为。
"""

import importlib.util
import sys
import types
from pathlib import Path

from sqlalchemy import String
from sqlalchemy.orm import declarative_base

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

# utils.config 模块底部有全局单例，import 时要求 backend/config/config.yaml 存在（已gitignore）。
# 本地缺失时临时创建，测试结束恢复。
_default_config_yaml = _backend_root / "config" / "config.yaml"
_created_default_config = False
if not _default_config_yaml.exists():
    _default_config_yaml.write_text("app:\n  name: taosha-test\n", encoding="utf-8")
    _created_default_config = True


def _cleanup_default_config():
    if _created_default_config:
        try:
            _default_config_yaml.unlink()
        except OSError:
            pass


def _load_wide_table_model():
    """加载宽表模型模块（stub 掉依赖数据库连接的 models.db_base）"""
    db_base_module = types.ModuleType("models.db_base")
    db_base_module.Base = declarative_base()
    models_module = types.ModuleType("models")
    fraudhunter_module = types.ModuleType("models.fraudhunter")
    sys.modules["models"] = models_module
    sys.modules["models.fraudhunter"] = fraudhunter_module
    sys.modules["models.db_base"] = db_base_module

    module_path = _backend_root / "models" / "fraudhunter" / "wide_table.py"
    spec = importlib.util.spec_from_file_location("wide_table_model_for_test", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestStorageBackendField:
    """模型字段定义测试"""

    def test_field_exists_on_snapshot(self):
        module = _load_wide_table_model()
        table = module.FraudHunterWideTableSnapshot.__table__
        assert "storage_backend" in table.columns

    def test_field_definition(self):
        module = _load_wide_table_model()
        col = module.FraudHunterWideTableSnapshot.__table__.columns["storage_backend"]

        assert isinstance(col.type, String)
        assert col.type.length == 16
        assert col.nullable is False
        # Python侧默认值兜底：不显式赋值的新快照落为 postgresql
        assert col.default is not None
        assert col.default.arg == "postgresql"
        assert "postgresql" in col.comment and "duckdb" in col.comment

    def test_version_model_untouched(self):
        """版本表不加字段（版本/哈希逻辑与存储无关）"""
        module = _load_wide_table_model()
        assert "storage_backend" not in module.FraudHunterWideTableVersion.__table__.columns

    def test_model_matches_migration_sql(self):
        """迁移SQL与模型定义一致：VARCHAR(16) NOT NULL DEFAULT 'postgresql'"""
        migration_path = _backend_root / "migrations" / "add_snapshot_storage_backend.sql"
        migration_sql = migration_path.read_text(encoding="utf-8")

        assert "ADD COLUMN storage_backend VARCHAR(16)" in migration_sql
        assert "NOT NULL DEFAULT 'postgresql'" in migration_sql
        assert "fraudhunter_wide_table_snapshot" in migration_sql


class TestOfflineStoreConfig:
    """配置项默认值与读取测试（默认 postgresql，零行为变化）"""

    def _make_config(self, tmp_path: Path, wide_table_yaml: str):
        wide_table_lines = "\n".join(
            f"    {line}" for line in wide_table_yaml.strip("\n").splitlines()
        )
        yaml_content = (
            "app:\n"
            "  name: test\n"
            "database:\n"
            f"  dir: {tmp_path / 'dbdir'}\n"
            "fraudhunter:\n"
            "  wide_table:\n"
            f"{wide_table_lines}\n"
        )
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml_content, encoding="utf-8")

        from utils.config import ConfigManager
        return ConfigManager(config_path=str(config_path)).get_settings()

    def test_defaults_when_absent(self, tmp_path):
        """配置缺省时 offline_store=postgresql，行为与现状一致"""
        settings = self._make_config(tmp_path, 'sync_lookback_days: 30')
        assert settings.fraudhunter_wide_table_offline_store == "postgresql"
        assert settings.fraudhunter_wide_table_duckdb_compression == "zstd"
        assert settings.fraudhunter_wide_table_duckdb_staging_ttl_hours == 24
        assert "wide_tables_parquet" in settings.fraudhunter_wide_table_duckdb_storage_path

    def test_values_read_when_present(self, tmp_path):
        settings = self._make_config(
            tmp_path,
            'offline_store: "duckdb"\n'
            "duckdb:\n"
            '  storage_path: "/data/custom/parquet"\n'
            '  compression: "snappy"\n'
            "  staging_ttl_hours: 48\n",
        )
        assert settings.fraudhunter_wide_table_offline_store == "duckdb"
        assert settings.fraudhunter_wide_table_duckdb_storage_path == "/data/custom/parquet"
        assert settings.fraudhunter_wide_table_duckdb_compression == "snappy"
        assert settings.fraudhunter_wide_table_duckdb_staging_ttl_hours == 48

    def test_invalid_store_value_passthrough(self, tmp_path):
        """非法取值在本阶段不报错（阶段2工厂层做白名单校验），仅确认透传"""
        settings = self._make_config(tmp_path, 'offline_store: "mysql"')
        assert settings.fraudhunter_wide_table_offline_store == "mysql"

    def test_example_yaml_uses_default_backend(self):
        """示例配置的 offline_store 默认值必须为 postgresql（部署安全）"""
        example = (_backend_root / "config" / "config.yaml.example").read_text(encoding="utf-8")
        assert 'offline_store: "postgresql"' in example


import atexit
atexit.register(_cleanup_default_config)
