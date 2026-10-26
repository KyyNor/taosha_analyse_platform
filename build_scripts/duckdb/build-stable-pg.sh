#!/usr/bin/env bash
# 构建 Taosha DuckDB Service 应用镜像（只复制服务代码，可离线执行）
#
# 前置: Base 镜像已存在（联网机器 ./build-base.sh --save → 内网 docker load）
#
# 用法:
#   ./build-stable-pg.sh                    # 构建应用镜像
#   ./build-stable-pg.sh --offline          # 以 --network=none 验证零联网构建
#   ./build-stable-pg.sh --verify           # 构建 + 隔离环境集成测试
#   ./build-stable-pg.sh --verify --offline # 两者同时
set -euo pipefail
cd "$(dirname "$0")"

BASE_IMAGE="${DUCKDB_BASE_IMAGE:-taosha-duckdb-runtime:2.0.0-r1}"
APP_IMAGE="${DUCKDB_APP_IMAGE:-taosha-duckdb-service:2.0.0-pg}"
PLATFORM="linux/amd64"
VERIFY=0
OFFLINE=0

for arg in "$@"; do
  case "$arg" in
    --verify) VERIFY=1 ;;
    --offline) OFFLINE=1 ;;
    *) echo "Usage: $0 [--verify] [--offline]" >&2; exit 2 ;;
  esac
done

if ! docker image inspect "${BASE_IMAGE}" >/dev/null 2>&1; then
  echo "ERROR: 基础镜像不存在: ${BASE_IMAGE}" >&2
  echo "       联网机器执行 ./build-base.sh --save，内网 docker load 后再构建" >&2
  exit 1
fi

build_args=(--platform "${PLATFORM}" --load
  --build-arg "BASE_IMAGE=${BASE_IMAGE}"
  -f Dockerfile -t "${APP_IMAGE}" .)
if [[ "${OFFLINE}" == "1" ]]; then
  build_args+=(--network=none)
fi

echo "==> 构建 ${APP_IMAGE} (FROM ${BASE_IMAGE})"
docker buildx build "${build_args[@]}"

if [[ "${VERIFY}" == "1" ]]; then
  export DUCKDB_APP_IMAGE="${APP_IMAGE}"
  project="duckdb-stable-verify-$$"
  compose=(docker compose -p "$project" -f docker-compose.verify.yml)
  cleanup() { "${compose[@]}" down -v --remove-orphans; }
  trap cleanup EXIT
  "${compose[@]}" up -d --wait --wait-timeout 180 duckdb postgres
  "${compose[@]}" run --rm verify
  "${compose[@]}" restart duckdb
  "${compose[@]}" up -d --wait --wait-timeout 120 duckdb
  "${compose[@]}" run --rm -e PERSIST_ONLY=1 verify
fi

echo "完成: ${APP_IMAGE}"
