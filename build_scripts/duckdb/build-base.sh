#!/usr/bin/env bash
# 联网构建 DuckDB Runtime Base（依赖/扩展变更时才执行）
#
# 用法:
#   ./build-base.sh            # 构建 + 容器内离线扩展自检
#   ./build-base.sh --save     # 额外导出 tar.gz 与 SHA256（交付内网用）
#
# 产物:
#   taosha-duckdb-runtime:2.0.0-r1
#   dist/taosha-duckdb-runtime-2.0.0-r1-linux-amd64.tar.gz (+ .sha256)
set -euo pipefail
cd "$(dirname "$0")"

DUCKDB_VERSION="2.0.0"
REVISION="r1"
IMAGE="taosha-duckdb-runtime:${DUCKDB_VERSION}-${REVISION}"
PLATFORM="linux/amd64"
SAVE=0

for arg in "$@"; do
  case "$arg" in
    --save) SAVE=1 ;;
    *) echo "Usage: $0 [--save]" >&2; exit 2 ;;
  esac
done

echo "==> 构建 ${IMAGE} (${PLATFORM}, duckdb==${DUCKDB_VERSION})"
docker buildx build --platform "${PLATFORM}" --load \
  -f Dockerfile.base -t "${IMAGE}" .

echo "==> 离线扩展自检（--network=none）"
docker run --rm -i --platform "${PLATFORM}" --network none \
  --entrypoint python "${IMAGE}" - <<'EOF'
import duckdb

assert duckdb.__version__ == "2.0.0", duckdb.__version__
con = duckdb.connect()
con.execute("SET autoinstall_known_extensions=false")
con.execute("SET autoload_known_extensions=false")
for ext in ("postgres", "quack", "httpfs", "json", "parquet", "icu"):
    con.execute(f"LOAD {ext}")
print("PASS: 6 extensions offline |", con.sql("SELECT version()").fetchall()[0][0])
EOF

if [[ "${SAVE}" == "1" ]]; then
  mkdir -p dist
  archive="dist/taosha-duckdb-runtime-${DUCKDB_VERSION}-${REVISION}-linux-amd64.tar.gz"
  echo "==> 导出 ${archive}"
  docker save "${IMAGE}" | gzip > "${archive}"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${archive}" > "${archive}.sha256"
  else
    shasum -a 256 "${archive}" > "${archive}.sha256"
  fi
  cat "${archive}.sha256"
fi

echo "完成: ${IMAGE}"
