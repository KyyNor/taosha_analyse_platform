"""DuckDB Quack 服务端: 打开持久库, 启动 quack_serve, 常驻.

环境变量:
    DUCKDB_DB_PATH  数据库文件, 默认 /data/duck.db
    QUACK_BIND      监听地址, 默认 0.0.0.0
    QUACK_PORT      监听端口, 默认 9494
    QUACK_TOKEN     认证 token (必填, >= 4 字符)
    PG_ATTACH_DSN   可选: libpq 连接串。设置后在启动时 ATTACH 为 pg_rt (READ_ONLY),
                    供查询 SQL 引用 pg_rt.public.*; 失败仅告警不退出 (重试=重启容器)
"""
import os
import signal
import sys
import time

import duckdb

DUCKDB_DB_PATH = os.environ.get("DUCKDB_DB_PATH", "/data/duck.db")
QUACK_BIND = os.environ.get("QUACK_BIND", "0.0.0.0")
QUACK_PORT = os.environ.get("QUACK_PORT", "9494")
QUACK_TOKEN = os.environ.get("QUACK_TOKEN", "")
PG_ATTACH_DSN = os.environ.get("PG_ATTACH_DSN", "")

if len(QUACK_TOKEN) < 4:
    print("ERROR: QUACK_TOKEN 未设置或不足 4 个字符", file=sys.stderr, flush=True)
    sys.exit(1)

os.makedirs(os.path.dirname(DUCKDB_DB_PATH) or ".", exist_ok=True)

con = duckdb.connect(DUCKDB_DB_PATH)
con.sql("LOAD quack")

if PG_ATTACH_DSN:
    escaped = PG_ATTACH_DSN.replace("\\", "\\\\").replace("'", "\\'")
    try:
        con.sql("LOAD postgres;")
        con.sql(f"ATTACH '{escaped}' AS pg_rt (TYPE POSTGRES, READ_ONLY);")
        print("[server] ATTACH pg_rt (READ_ONLY) 成功", flush=True)
    except Exception as e:
        # 降级: 不阻塞服务启动, 引用 pg_rt 的查询会报错
        print(f"[server] WARN: ATTACH pg_rt 失败 (引用 pg_rt 的查询将报错): {e}",
              flush=True)

rows = con.sql(
    f"CALL quack_serve('quack:{QUACK_BIND}:{QUACK_PORT}', "
    f"token => '{QUACK_TOKEN}', allow_other_hostname => true)"
).fetchall()
print(f"[server] duckdb={duckdb.__version__} serving={rows[0][0]} url={rows[0][1]}", flush=True)

running = True


def _stop(*_):
    global running
    running = False


signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)

while running:
    time.sleep(1)

con.sql(f"CALL quack_stop('quack:{QUACK_BIND}:{QUACK_PORT}')")
con.close()
print("[server] stopped cleanly", flush=True)
