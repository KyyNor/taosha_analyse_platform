# Taosha DuckDB Service 应用镜像：只叠加服务代码，不装依赖
#   FROM taosha-duckdb-runtime（Dockerfile.base）
#   服务: Quack 9494 + HTTP 网关 9495, 数据卷 /data
#
# 不写 `# syntax=` 前端指令：内网无外网拉取 dockerfile 前端镜像时也能构建。
#
# 构建（Base 已 load 后可在内网离线执行）:
#   ./build-stable-pg.sh             # 构建应用镜像
#   ./build-stable-pg.sh --offline   # 以 --network=none 验证零联网构建
#   ./build-stable-pg.sh --verify    # 构建 + 隔离环境集成测试
ARG BASE_IMAGE=taosha-duckdb-runtime:2.0.0-r1
FROM ${BASE_IMAGE}

WORKDIR /app
COPY server.py gateway.py healthcheck.py entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

HEALTHCHECK --interval=5s --timeout=3s --start-period=20s --retries=12 \
  CMD ["python", "/app/healthcheck.py"]

ENTRYPOINT ["/app/entrypoint.sh"]
