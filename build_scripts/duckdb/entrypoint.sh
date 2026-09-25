#!/usr/bin/env bash
# 单容器双进程: duckdb 服务端 (9494, quack 协议) + HTTP 网关 (9495, JSON)。
# 任一进程退出则容器退出 (交给 compose 的 restart 策略拉起)。
set -uo pipefail

export DUCKDB_DB_PATH="${DUCKDB_DB_PATH:-/data/duck.db}"
export QUACK_BIND="${QUACK_BIND:-0.0.0.0}"
export QUACK_PORT="${QUACK_PORT:-9494}"
export GATEWAY_PORT="${GATEWAY_PORT:-9495}"
# 网关在容器内经 loopback 连服务端
export QUACK_URI="${QUACK_URI:-quack:127.0.0.1:${QUACK_PORT}}"

QUACK_TOKEN="${QUACK_TOKEN:-}"
if [ "${#QUACK_TOKEN}" -lt 4 ]; then
  echo "ERROR: QUACK_TOKEN 未设置或不足 4 个字符" >&2
  exit 1
fi

python /app/server.py &
SERVER_PID=$!

python -m uvicorn gateway:app --host 0.0.0.0 --port "${GATEWAY_PORT}" \
  --app-dir /app --workers 1 &
GATEWAY_PID=$!

term() {
  kill "${SERVER_PID}" "${GATEWAY_PID}" 2>/dev/null
}
trap term TERM INT

# 任一子进程退出即返回
wait -n "${SERVER_PID}" "${GATEWAY_PID}"
code=$?
term
wait 2>/dev/null
exit "${code}"
