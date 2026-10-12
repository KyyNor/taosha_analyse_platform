#!/usr/bin/env python3
"""DuckDB Quack 服务端远程查询测试.

用法:
    QUACK_URI=quack:127.0.0.1:9494 QUACK_TOKEN=xxx python test_remote_query.py

环境变量:
    QUACK_URI     服务端地址, 默认 quack:127.0.0.1:9494
    QUACK_TOKEN   认证 token (必填)
    PERSIST_ONLY  设为 1 时跳过建表, 只校验之前建的表还存在 (用于重启持久化验证)

覆盖:
    1. HTTP 健康检查 (GET /)
    2. 无状态远程查询 quack_query()
    3. ATTACH 远程库 + 建表 + 写入 + 读回 + 聚合
"""
import os
import sys
import urllib.request

import duckdb

QUACK_URI = os.environ.get("QUACK_URI", "quack:127.0.0.1:9494")
QUACK_TOKEN = os.environ["QUACK_TOKEN"]
PERSIST_ONLY = os.environ.get("PERSIST_ONLY") == "1"

TABLE = "quack_test_rows"


def check(name, fn):
    try:
        result = fn()
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] {name}: {type(e).__name__}: {e}")
        sys.exit(1)
    print(f"[OK]   {name}: {result}")


def http_health():
    # quack:host:port -> http://host:port/
    rest = QUACK_URI.split("quack:", 1)[1]
    host, _, port = rest.rpartition(":")
    if not host:
        host, port = rest, "9494"
    with urllib.request.urlopen(f"http://{host}:{port}/", timeout=10) as r:
        body = r.read().decode().strip()
    assert "DuckDB Quack RPC endpoint" in body, f"unexpected body: {body!r}"
    return body


def main():
    print(f"client library : {duckdb.sql('SELECT version()').fetchone()[0]}")
    print(f"target server  : {QUACK_URI}")

    check("HTTP health (GET /)", http_health)

    con = duckdb.connect()
    con.sql("INSTALL quack")  # 已安装时为幂等操作
    con.sql("LOAD quack")

    # 非本机地址时客户端默认走 HTTPS, 本服务端未配 TLS, 必须 disable_ssl
    check(
        "stateless quack_query",
        lambda: con.sql(
            f"SELECT * FROM quack_query('{QUACK_URI}', 'SELECT 42 AS answer', "
            f"token => '{QUACK_TOKEN}', disable_ssl => true)"
        ).fetchone(),
    )

    con.sql(
        f"ATTACH '{QUACK_URI}' AS remote (TYPE quack, TOKEN '{QUACK_TOKEN}', DISABLE_SSL true)"
    )
    try:
        if PERSIST_ONLY:
            rows = con.sql(f"SELECT count(*), sum(i) FROM remote.{TABLE}").fetchone()
            assert rows == (100, 4950), f"persistence mismatch: {rows}"
            return rows
        con.sql(f"DROP TABLE IF EXISTS remote.{TABLE}")
        con.sql(
            f"CREATE TABLE remote.{TABLE} AS "
            f"SELECT range AS i, 'row_' || range AS s FROM range(100)"
        )
        check(
            "remote table write (100 rows)",
            lambda: con.sql(f"SELECT count(*) FROM remote.{TABLE}").fetchone(),
        )
        check(
            "remote aggregate pushdown",
            lambda: con.sql(f"SELECT count(*), sum(i) FROM remote.{TABLE}").fetchone(),
        )
        check(
            "remote filter",
            lambda: con.sql(
                f"SELECT s FROM remote.{TABLE} WHERE i = 7"
            ).fetchone(),
        )
        return None
    finally:
        con.sql("DETACH remote")


if __name__ == "__main__":
    main()
    print("ALL REMOTE QUERY TESTS PASSED")
