# syntax=docker/dockerfile:1
# DuckDB 2.0.0 LTS: Quack (9494), HTTP gateway (9495), PostgreSQL connector.
# Build: docker buildx build --platform linux/amd64 --load -t duckdb-quack:2.0.0-pg .
FROM python:3.12-slim-bookworm

ARG TARGETARCH
RUN test "$TARGETARCH" = "amd64"

RUN apt-get update && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir duckdb==2.0.0 fastapi==0.119.0 uvicorn==0.37.0

# Install into the runtime user's cache; verify signed release extensions offline.
RUN python - <<'EOF'
import duckdb
assert duckdb.__version__ == "2.0.0"
c = duckdb.connect()
assert c.sql("SELECT version()").fetchall()[0][0] == "v2.0.0"
for ext in ("postgres", "quack", "httpfs", "json", "parquet", "icu"):
    c.execute(f"INSTALL {ext}")
c.execute("SET autoinstall_known_extensions=false")
c.execute("SET autoload_known_extensions=false")
for ext in ("postgres", "quack", "httpfs", "json", "parquet", "icu"):
    c.execute(f"LOAD {ext}")
print(c.sql("SELECT extension_name, extension_version FROM duckdb_extensions() WHERE loaded").fetchall())
EOF

COPY server.py gateway.py healthcheck.py entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh
ENV DUCKDB_DB_PATH=/data/duck.db \
    QUACK_BIND=0.0.0.0 \
    QUACK_PORT=9494 \
    GATEWAY_PORT=9495
EXPOSE 9494 9495
VOLUME /data
HEALTHCHECK --interval=5s --timeout=3s --start-period=20s --retries=12 \
  CMD ["python", "/app/healthcheck.py"]
ENTRYPOINT ["/app/entrypoint.sh"]
