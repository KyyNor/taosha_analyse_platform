#!/usr/bin/env python3
"""duckdb-quack:2.0-alpha-pg 镜像最小验证测试.

覆盖三项基础能力（在镜像自身的运行环境内执行, 不依赖外部网络）:
1. DuckDB 版本: pip 包与底层库均为固定值（不浮动 latest 的证明）;
2. PostgreSQL Connector 离线加载: 关闭 autoinstall 后 LOAD postgres 仍成功
   （扩展二进制已预装进镜像, 启动后无需临时下载）;
3. PostgreSQL attach/connect 基础能力: 读写 ATTACH 验证库, 建表/写入/读回/过滤往返;
   外加经 quack 服务端 (容器 9494) 的远程查询透传验证.

用法（由 docker-compose.alpha-pg.yml 的 verify profile 调用）:
    PG_DSN="dbname=.. host=.. port=.. user=.. password=.." \
    QUACK_URI=quack:duckdb-quack-pg:9494 QUACK_TOKEN=xxx \
    python test_postgres_connector.py
"""
import os
import sys
import urllib.request

import duckdb

PIP_VERSION = os.environ.get("DUCKDB_PIP_VERSION", "2.0.0.dev2609222040")
LIBRARY_VERSION = "v2.0.0-alpha43089"
QUACK_URI = os.environ.get("QUACK_URI", "quack:duckdb-quack-pg:9494")
QUACK_TOKEN = os.environ.get("QUACK_TOKEN", "dev-token-please-change")
PG_DSN = os.environ.get(
    "PG_DSN", "dbname=pgverify host=pg-verify port=5432 user=pgverify password=pgverify")


def check(name, fn):
    try:
        result = fn()
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] {name}: {type(e).__name__}: {e}")
        sys.exit(1)
    print(f"[OK]   {name}: {result}")
    return result


def check_versions():
    lib = duckdb.sql("SELECT version()").fetchone()[0]
    assert duckdb.__version__ == PIP_VERSION, (
        f"pip 版本漂移: {duckdb.__version__} != {PIP_VERSION}")
    assert lib == LIBRARY_VERSION, f"库版本漂移: {lib} != {LIBRARY_VERSION}"
    return f"pip={duckdb.__version__} library={lib}"


def check_postgres_offline_load():
    """关闭自动安装后 LOAD postgres 必须仍成功（预装证明）"""
    con = duckdb.connect()
    con.sql("SET autoinstall_known_extensions=false")
    con.sql("SET autoload_known_extensions=false")
    con.sql("LOAD postgres")
    ext = con.sql(
        "SELECT extension_name, extension_version FROM duckdb_extensions() "
        "WHERE extension_name='postgres_scanner' AND loaded"
    ).fetchall()
    assert ext, "postgres_scanner 未加载"
    return f"postgres_scanner {ext[0][1]} (offline)"


def check_postgres_attach_roundtrip():
    """读写 ATTACH PostgreSQL：建表/写入/读回/过滤往返"""
    con = duckdb.connect()
    con.sql("LOAD postgres")
    con.sql(f"ATTACH '{PG_DSN}' AS pg_check (TYPE POSTGRES)")
    try:
        con.sql("DROP TABLE IF EXISTS pg_check.public.alpha_pg_verify")
        con.sql(
            "CREATE TABLE pg_check.public.alpha_pg_verify AS "
            "SELECT range AS i, 'row_' || range AS s FROM range(100)")
        total = con.sql(
            "SELECT count(*), sum(i) FROM pg_check.public.alpha_pg_verify").fetchone()
        assert total == (100, 4950), total
        filtered = con.sql(
            "SELECT s FROM pg_check.public.alpha_pg_verify WHERE i = 7").fetchone()
        assert filtered == ("row_7",), filtered
        return f"attach+roundtrip rows={total[0]} sum={total[1]}"
    finally:
        con.sql("DETACH pg_check")


def check_quack_remote_passthrough():
    """经 quack 服务端远程查询（镜像内 9494 端口的双进程形态可用）"""
    con = duckdb.connect()
    con.sql("INSTALL quack")  # 已预装, 幂等
    con.sql("LOAD quack")
    row = con.sql(
        f"SELECT * FROM quack_query('{QUACK_URI}', "
        f"'SELECT 42 AS answer', token => '{QUACK_TOKEN}', disable_ssl => true)"
    ).fetchone()
    assert row == (42,), row

    # 服务端已按 PG_ATTACH_DSN 常驻 ATTACH pg_rt（只读）：经远程查询引用验证
    remote_pg = con.sql(
        f"SELECT * FROM quack_query('{QUACK_URI}', "
        f"'SELECT count(*) FROM pg_rt.public.alpha_pg_verify', "
        f"token => '{QUACK_TOKEN}', disable_ssl => true)"
    ).fetchone()
    assert remote_pg == (100,), remote_pg
    return f"quack passthrough=42, pg_rt rows={remote_pg[0]}"


def check_gateway_health():
    rest = QUACK_URI.split("quack:", 1)[1]
    host, _, port = rest.rpartition(":")
    host = host or "127.0.0.1"
    with urllib.request.urlopen(f"http://{host}:{port}/", timeout=10) as r:
        body = r.read().decode().strip()
    assert "DuckDB Quack RPC endpoint" in body, body
    return "HTTP health OK"


def main():
    print(f"pip/package   : {duckdb.__version__}")
    print(f"library       : {duckdb.sql('SELECT version()').fetchone()[0]}")
    print(f"pg dsn        : {PG_DSN.split('password=')[0]}***")
    print(f"quack target  : {QUACK_URI}")

    check("版本固定（pip + library）", check_versions)
    check("HTTP health (服务端 9494)", check_gateway_health)
    check("postgres 扩展离线加载", check_postgres_offline_load)
    check("PostgreSQL attach/connect 往返", check_postgres_attach_roundtrip)
    check("quack 远程查询 + pg_rt 引用", check_quack_remote_passthrough)


if __name__ == "__main__":
    main()
    print("ALL POSTGRES CONNECTOR TESTS PASSED")
