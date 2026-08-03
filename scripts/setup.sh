#!/usr/bin/env bash
# Idempotent first-time / refresh setup: deps, data stack, migrate, seed, Ollama model.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

POSTGRES_PORT="${POSTGRES_PORT:-5434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3.5:4b}"
OLLAMA_EMBED_MODEL="${OLLAMA_EMBED_MODEL:-nomic-embed-text}"

echo "==> Environment files"
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi
if [[ ! -f backend/.env ]]; then
  cp backend/.env.example backend/.env
  echo "Created backend/.env from backend/.env.example"
fi

# Keep host-side DATABASE_URL aligned with Compose Postgres settings.
set -a
# shellcheck disable=SC1091
source "$ROOT/.env"
set +a
DATABASE_URL="postgresql+psycopg://${POSTGRES_USER:-assessgen}:${POSTGRES_PASSWORD:-assessgen}@localhost:${POSTGRES_PORT:-5433}/${POSTGRES_DB:-assessgen}"
if grep -q '^DATABASE_URL=' "$ROOT/backend/.env"; then
  if [[ "$(uname)" == "Darwin" ]]; then
    sed -i '' "s|^DATABASE_URL=.*|DATABASE_URL=${DATABASE_URL}|" "$ROOT/backend/.env"
  else
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${DATABASE_URL}|" "$ROOT/backend/.env"
  fi
else
  echo "DATABASE_URL=${DATABASE_URL}" >>"$ROOT/backend/.env"
fi
echo "Synced backend/.env DATABASE_URL -> localhost:${POSTGRES_PORT:-5433}"

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

echo "==> Ollama models"
pull_ollama_model_host() {
  local model="$1"
  if ollama show "$model" >/dev/null 2>&1; then
    echo "Model ${model} already present (host)"
  else
    echo "Pulling ${model} on host..."
    ollama pull "$model"
  fi
}

pull_ollama_model_container() {
  local model="$1"
  if docker exec assessgen-ollama ollama show "$model" >/dev/null 2>&1; then
    echo "Model ${model} already present (container)"
  else
    echo "Pulling ${model} in assessgen-ollama..."
    docker exec assessgen-ollama ollama pull "$model"
  fi
}

if [[ "${SKIP_OLLAMA_PULL:-0}" == "1" ]]; then
  echo "Skipping Ollama pulls (SKIP_OLLAMA_PULL=1)"
else
  if command -v ollama >/dev/null 2>&1; then
    pull_ollama_model_host "$OLLAMA_MODEL"
    pull_ollama_model_host "$OLLAMA_EMBED_MODEL"
  else
    echo "Ollama CLI not found on host — skip host pull"
  fi

  if docker ps --format '{{.Names}}' | grep -qx assessgen-ollama; then
    pull_ollama_model_container "$OLLAMA_MODEL"
    pull_ollama_model_container "$OLLAMA_EMBED_MODEL"
  fi
fi

echo "Setup complete."
