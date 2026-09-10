# syntax=docker/dockerfile:1
# DuckDB "2.0 alpha" 单容器镜像: quack 服务端 (9494) + HTTP 网关 (9495)
#
# 客户端选择:
#   - 机器 glibc >= 2.27: 直连 9494 (quack 协议, pip install --pre duckdb 或官方 CLI)
#   - 机器 glibc < 2.27 (如 CentOS 7): 走 9495 网关 (只需 curl), 或用
#     build-portable-client.sh 生成的 musl 便携客户端直连 9494
#
# 版本选择说明 (2026-09-09 现状):
#   - v2.0 已于 2026-09-02 feature freeze (分支 v2.0-cyanoptera), 正式版目标 2026 年 10 月下旬
#   - cyanoptera 分支的 CLI 快照没有配套扩展二进制 (官方扩展仓库只保留最新 alpha 频道)
#   - pip install duckdb --pre == 1.6.0.dev379 (底层库 v2.0.0-alpha39998), 全平台工作正常,
#     本镜像服务端与网关均基于它 (官方 alpha CLI 的 linux 版 quack 扩展存在服务端认证 bug, 不用)

FROM python:3.12-slim

# duckdb (quack 客户端/服务端) + 网关框架
RUN pip install --no-cache-dir --pre duckdb==1.6.0.dev379 fastapi uvicorn \
 && python -c "import duckdb; c=duckdb.connect(); c.sql('INSTALL quack; LOAD quack'); \
print('duckdb', duckdb.__version__, '| library', c.sql('SELECT version()').fetchone()[0], \
'| quack', c.sql(\"SELECT extension_version FROM duckdb_extensions() WHERE extension_name='quack'\").fetchone()[0])"

COPY server.py gateway.py entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

RUN apt-get update && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

ENV DUCKDB_DB_PATH=/data/duck.db \
    QUACK_BIND=0.0.0.0 \
    QUACK_PORT=9494 \
    GATEWAY_PORT=9495

EXPOSE 9494 9495
VOLUME /data

# 健康检查要求两个端口都可用
HEALTHCHECK --interval=5s --timeout=3s --start-period=20s --retries=12 \
  CMD curl -fsS "http://127.0.0.1:${QUACK_PORT}/" >/dev/null \
   && curl -fsS "http://127.0.0.1:${GATEWAY_PORT}/health" >/dev/null || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
