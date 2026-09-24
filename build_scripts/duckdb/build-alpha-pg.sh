#!/usr/bin/env bash
# 构建 duckdb-quack:2.0-alpha-pg 镜像（DuckDB 2.0 Alpha + 预装 PostgreSQL Connector）
#
# 用法:
#   ./build-alpha-pg.sh              # 仅构建镜像
#   ./build-alpha-pg.sh --verify     # 构建后起 compose 跑最小验证测试（需要 Docker）
#
# 版本固定（与 Dockerfile.alpha-pg ARG 保持一致；升级时两处同步修改）:
#   pip 包  : duckdb==2.0.0.dev2609222040
#   库版本  : v2.0.0-alpha43089
set -euo pipefail

cd "$(dirname "$0")"

DUCKDB_PIP_VERSION="2.0.0.dev2609222040"
IMAGE_TAG="duckdb-quack:2.0-alpha-pg"

echo "==> 构建 ${IMAGE_TAG} (duckdb==${DUCKDB_PIP_VERSION}, v2.0.0-alpha43089, postgres/quack 扩展预装)"
docker build -f Dockerfile.alpha-pg \
  --build-arg DUCKDB_PIP_VERSION="${DUCKDB_PIP_VERSION}" \
  -t "${IMAGE_TAG}" .

echo "==> 镜像内版本自检"
docker run --rm --entrypoint python "${IMAGE_TAG}" - <<'EOF'
import duckdb
assert duckdb.__version__ == "2.0.0.dev2609222040", duckdb.__version__
c = duckdb.connect()
lib = c.sql("SELECT version()").fetchone()[0]
assert lib == "v2.0.0-alpha43089", lib
print(f"duckdb pip={duckdb.__version__} library={lib}")
EOF

if [[ "${1:-}" == "--verify" ]]; then
  echo "==> 启动 compose（含验证用 PostgreSQL）并执行最小验证测试"
  # 只长跑服务端与 PG（一次性 verify 容器不适合 --wait，单独 run）
  docker compose -f docker-compose.alpha-pg.yml up -d --wait duckdb-quack-pg pg-verify-db
  docker compose -f docker-compose.alpha-pg.yml run --rm pg-verify
  status=$?
  echo "==> 清理验证环境（保留镜像）"
  docker compose -f docker-compose.alpha-pg.yml --profile verify down -v
  exit "${status}"
fi

echo "完成: ${IMAGE_TAG}"
