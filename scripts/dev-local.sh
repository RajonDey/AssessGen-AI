#!/usr/bin/env bash
# Run backend + admin locally without Docker (uses host Ollama or paid API).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f backend/.env ]]; then
  cp backend/.env.example backend/.env
fi
if [[ ! -f admin/.env.local ]]; then
  cp admin/.env.example admin/.env.local
fi

echo "==> Backend deps"
cd "$ROOT/backend"
if ! command -v uv >/dev/null 2>&1; then
  echo "Install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi
uv sync

echo "==> Admin deps"
cd "$ROOT/admin"
if [[ ! -d node_modules ]]; then
  npm install
fi

echo "==> Starting API on :8080 and admin on :3001"
echo "    Ensure Ollama is running if LLM_PROVIDER=ollama"
cd "$ROOT/backend"
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8080 &
API_PID=$!

cd "$ROOT/admin"
npm run dev &
ADMIN_PID=$!

cleanup() {
  kill "$API_PID" "$ADMIN_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "API  http://127.0.0.1:8080/api/docs"
echo "UI   http://127.0.0.1:3001/generate"
wait
