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
    # PG 未就绪（compose 并行启动等）时有界重试；超时降级为告警，不阻塞服务启动
    retry_seconds = float(os.environ.get("PG_ATTACH_RETRY_SECONDS", "60"))
    deadline = time.time() + retry_seconds
    while True:
        try:
            con.sql("LOAD postgres;")
            con.sql(f"ATTACH '{escaped}' AS pg_rt (TYPE POSTGRES, READ_ONLY);")
            print("[server] ATTACH pg_rt (READ_ONLY) 成功", flush=True)
            break
        except Exception as e:
            if time.time() >= deadline:
                # 降级: 不阻塞服务启动, 引用 pg_rt 的查询会报错
                print(f"[server] WARN: ATTACH pg_rt 失败 "
                      f"(重试{retry_seconds}s后放弃, 引用 pg_rt 的查询将报错): {e}",
                      flush=True)
                break
            print(f"[server] PG 未就绪, 2s 后重试 ATTACH pg_rt: {e}", flush=True)
            time.sleep(2)

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
