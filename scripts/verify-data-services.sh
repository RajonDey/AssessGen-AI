#!/usr/bin/env bash
# Verify data profile services (Postgres + pgvector, Redis, MinIO).
set -euo pipefail

POSTGRES_USER="${POSTGRES_USER:-assessgen}"
POSTGRES_DB="${POSTGRES_DB:-assessgen}"
POSTGRES_PORT="${POSTGRES_PORT:-5433}"
REDIS_PORT="${REDIS_PORT:-6379}"
MINIO_CONSOLE_PORT="${MINIO_CONSOLE_PORT:-9001}"

echo "==> Postgres version"
docker exec assessgen-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT version();"

echo "==> pgvector extension"
docker exec assessgen-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
  "SELECT extname FROM pg_extension WHERE extname = 'vector';"

echo "==> Redis ping"
docker exec assessgen-redis redis-cli ping

echo "==> MinIO console reachable"
curl -sf "http://localhost:${MINIO_CONSOLE_PORT}/minio/health/live" >/dev/null
echo "MinIO OK"

echo "All data services healthy."
