#!/usr/bin/env bash
# Idempotent first-time / refresh setup: deps, data stack, migrate, seed, Ollama model.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

POSTGRES_PORT="${POSTGRES_PORT:-5433}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3.5:4b}"

echo "==> Environment files"
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi
if [[ ! -f backend/.env ]]; then
  cp backend/.env.example backend/.env
  echo "Created backend/.env from backend/.env.example"
fi

echo "==> Python dependencies (uv sync)"
cd "$ROOT/backend"
uv python install 3.12
uv sync --extra dev

echo "==> Docker data profile"
cd "$ROOT"
docker compose --profile data up -d

echo "==> Waiting for Postgres on port ${POSTGRES_PORT}"
for _ in $(seq 1 60); do
  if docker exec assessgen-postgres pg_isready -U "${POSTGRES_USER:-assessgen}" \
    -d "${POSTGRES_DB:-assessgen}" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

"$ROOT/scripts/verify-data-services.sh"

echo "==> Database migrations"
cd "$ROOT/backend"
uv run alembic upgrade head

echo "==> Seed data"
uv run python -m app.scripts.seed

echo "==> Ollama model (host CLI, if available)"
if command -v ollama >/dev/null 2>&1; then
  ollama pull "$OLLAMA_MODEL"
else
  echo "Ollama CLI not found — skip host pull (use 'make generate' and pull inside container)"
fi

echo "Setup complete."
