#!/usr/bin/env bash
# Build linux/amd64 release image; --verify runs isolated integration tests.
set -euo pipefail
cd "$(dirname "$0")"
if [[ $# -gt 1 || ( $# -eq 1 && "$1" != --verify ) ]]; then
  echo "Usage: $0 [--verify]" >&2
  exit 2
fi
docker buildx build --platform linux/amd64 --load -t duckdb-quack:2.0.0-pg .
if [[ "${1:-}" == --verify ]]; then
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
