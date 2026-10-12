"""
阶段 8：宽表快照表结构守卫（docs/fraudhunter_offline_dual_store_plan.md 7.x 阶段 8）

- 启动轻量迁移自动补 storage_backend 列（存量行回填 postgresql）；
- verify_wide_table_snapshot_schema：列缺失任何模式都拒绝；
  唯一索引未含 storage_backend 时仅 PG 模式放行。

在子进程中运行，使用 SQLite 模拟 MySQL 元数据库（避免污染其它测试的 sys.modules）。
"""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_backend_root = Path(__file__).parents[4] / "backend"
_config = Path(__file__).parents[1] / "pg_golden" / "config.golden.yaml"

_PRELUDE = f"""
import os, sys
os.environ['TAOSHA_CONFIG_FILE'] = {str(_config)!r}
sys.path.insert(0, {str(_backend_root)!r})
os.chdir({str(_backend_root)!r})
import services  # 按应用顺序初始化包，规避循环导入
from sqlalchemy import create_engine, inspect, text
import models.db_base as db_base

engine = create_engine('sqlite://')
def legacy_table(unique_cols):
    with engine.begin() as c:
        c.execute(text(
            "CREATE TABLE fraudhunter_wide_table_snapshot ("
            " id INTEGER PRIMARY KEY, wide_table_name VARCHAR(64), version_hash VARCHAR(64),"
            " etl_date DATE, parquet_file_path VARCHAR(512))"
        ))
        c.execute(text(
            "CREATE UNIQUE INDEX uk_fh_ws_table_date ON fraudhunter_wide_table_snapshot ("
            + ", ".join(unique_cols) + ")"
        ))
        c.execute(text(
            "INSERT INTO fraudhunter_wide_table_snapshot VALUES (1, 't', 'v', '2026-10-01', 't_v')"
        ))
"""


def _run(body: str) -> subprocess.CompletedProcess:
    code = _PRELUDE + textwrap.dedent(body)
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)


def _ok(proc):
    if proc.returncode != 0:
        pytest.fail(proc.stdout[-2000:] + proc.stderr[-3000:])
    return proc.stdout


def test_missing_column_rejected_in_every_mode():
    out = _ok(_run("""
        legacy_table(['wide_table_name', 'version_hash', 'etl_date'])
        for mode in ('postgresql', 'both', 'duckdb'):
            try:
                db_base.verify_wide_table_snapshot_schema(mode, bind=engine)
                print(mode, 'PASSED')
            except RuntimeError as e:
                print(mode, 'REJECTED', 'add_snapshot_storage_backend.sql' in str(e))
    """))
    assert "postgresql REJECTED True" in out
    assert "both REJECTED True" in out
    assert "duckdb REJECTED True" in out


def test_lightweight_migration_adds_column_with_postgresql_default():
    out = _ok(_run("""
        legacy_table(['wide_table_name', 'version_hash', 'etl_date'])
        with engine.begin() as conn:
            # SQLite 不支持 COMMENT 子句：去掉后执行与生产相同的补列语句
            class _Conn:
                def execute(self, clause):
                    return conn.execute(text(clause.text.replace(" COMMENT '存储后端: postgresql/duckdb'", "")))
            db_base._migrate_wide_table_snapshot_table(_Conn(), inspect(engine))
        with engine.connect() as conn:
            print('VALUES', [r[0] for r in conn.execute(text(
                'SELECT storage_backend FROM fraudhunter_wide_table_snapshot'))])
        db_base.verify_wide_table_snapshot_schema('postgresql', bind=engine)
        print('PG OK')
    """))
    assert "VALUES ['postgresql']" in out
    assert "PG OK" in out


def test_old_unique_index_only_allowed_for_postgresql():
    out = _ok(_run("""
        legacy_table(['wide_table_name', 'version_hash', 'etl_date'])
        with engine.begin() as c:
            c.execute(text("ALTER TABLE fraudhunter_wide_table_snapshot "
                           "ADD COLUMN storage_backend VARCHAR(16) NOT NULL DEFAULT 'postgresql'"))
        db_base.verify_wide_table_snapshot_schema('postgresql', bind=engine)
        print('postgresql PASSED')
        for mode in ('both', 'duckdb'):
            try:
                db_base.verify_wide_table_snapshot_schema(mode, bind=engine)
                print(mode, 'PASSED')
            except RuntimeError as e:
                print(mode, 'REJECTED', 'update_snapshot_unique_with_backend.sql' in str(e))
    """))
    assert "postgresql PASSED" in out
    assert "both REJECTED True" in out
    assert "duckdb REJECTED True" in out


def test_new_unique_index_allows_dual_store():
    out = _ok(_run("""
        legacy_table(['wide_table_name', 'version_hash', 'etl_date'])
        with engine.begin() as c:
            c.execute(text("ALTER TABLE fraudhunter_wide_table_snapshot "
                           "ADD COLUMN storage_backend VARCHAR(16) NOT NULL DEFAULT 'postgresql'"))
            c.execute(text("DROP INDEX uk_fh_ws_table_date"))
            c.execute(text("CREATE UNIQUE INDEX uk_fh_ws_table_date ON fraudhunter_wide_table_snapshot "
                           "(wide_table_name, version_hash, etl_date, storage_backend)"))
        for mode in ('postgresql', 'both', 'duckdb'):
            db_base.verify_wide_table_snapshot_schema(mode, bind=engine)
            print(mode, 'PASSED')
    """))
    assert out.count("PASSED") == 3


def test_fresh_database_passes():
    out = _ok(_run("""
        db_base.verify_wide_table_snapshot_schema('both', bind=engine)
        print('FRESH OK')
    """))
    assert "FRESH OK" in out
