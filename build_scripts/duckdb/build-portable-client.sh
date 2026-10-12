#!/usr/bin/env bash
# 生成 glibc 2.17 (CentOS 7) 等老系统可用的 duckdb quack 便携客户端包。
#
# 原理: 官方 musl 版 CLI 不链接系统 glibc, 配上 musl loader / libstdc++ / libgcc
# 四个文件即可在任意 x86_64 Linux 上运行 (已实测 CentOS 7 / glibc 2.17)。
#
# 用法:
#   ./build-portable-client.sh [输出目录]     # 默认 ./portable-client-amd64
#
# 产物:
#   portable-client-amd64/
#   ├── duckdb                  musl 版 CLI (v2.1.0-alpha40775)
#   ├── ld-musl-x86_64.so.1     musl loader (自带 musl libc)
#   ├── libstdc++.so.6          musl 版 C++ 运行库
#   ├── libgcc_s.so.1           musl 版 gcc 运行库
#   └── quack-remote.sh         使用示例脚本
#
# 目标机器上运行:
#   export LD_LIBRARY_PATH=/path/to/portable-client-amd64
#   /path/to/portable-client-amd64/ld-musl-x86_64.so.1 /path/to/portable-client-amd64/duckdb -unsigned -c "<SQL>"
#
# 注意: -unsigned 跳过扩展签名校验 (官方仓库未发布 musl 平台的扩展签名),
#       扩展仍从官方 extensions.duckdb.org 下载。
set -euo pipefail

OUT="${1:-portable-client-amd64}"
STAGING_BASE="https://duckdb-staging.duckdb.org/3ef446f67f/v2.1.0-alpha40775"

mkdir -p "${OUT}"

echo "[1/3] 下载 musl 版 duckdb CLI ..."
curl -fsSL "${STAGING_BASE}/duckdb/duckdb/github_release/duckdb-cli-linux-amd64-musl.tar.gz" \
  | tar -C "${OUT}" -xzf -

echo "[2/3] 从 alpine:3.20 提取 musl 运行库 ..."
docker run --rm --platform linux/amd64 alpine:3.20 sh -c \
  'apk add --no-cache libstdc++ >/dev/null 2>&1; cat /usr/lib/libstdc++.so.6' > "${OUT}/libstdc++.so.6"
docker run --rm --platform linux/amd64 alpine:3.20 sh -c \
  'apk add --no-cache libstdc++ >/dev/null 2>&1; cat /usr/lib/libgcc_s.so.1' > "${OUT}/libgcc_s.so.1"
docker run --rm --platform linux/amd64 alpine:3.20 cat /lib/ld-musl-x86_64.so.1 > "${OUT}/ld-musl-x86_64.so.1"
chmod +x "${OUT}"/*

echo "[3/3] 写入使用示例 quack-remote.sh ..."
cat > "${OUT}/quack-remote.sh" <<'EOS'
#!/usr/bin/env bash
# quack 远程查询示例: ./quack-remote.sh <host:port> <token> "<SQL>"
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
export LD_LIBRARY_PATH="${DIR}"
exec "${DIR}/ld-musl-x86_64.so.1" "${DIR}/duckdb" -unsigned -c "
INSTALL quack; LOAD quack;
ATTACH 'quack://$1' AS remote (TYPE quack, TOKEN '$2', DISABLE_SSL true);
$3
"
EOS
chmod +x "${OUT}/quack-remote.sh"

echo "完成: ${OUT}/  (共 $(du -sh ${OUT} | cut -f1))"
