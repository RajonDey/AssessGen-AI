#!/usr/bin/env bash
# Phase 1A exit verification — setup, tests, smoke generation run, worker restart.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8000}"
API_BASE="http://localhost:${API_PORT}/api/v1"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3.5:4b}"
POSTGRES_USER="${POSTGRES_USER:-assessgen}"
POSTGRES_DB="${POSTGRES_DB:-assessgen}"
ADMIN_EMAIL="${SEED_ADMIN_EMAIL:-admin@assessgen.local}"
ADMIN_PASSWORD="${SEED_ADMIN_PASSWORD:-admin}"

json_field() {
  local payload="$1"
  local field="$2"
  python3 -c 'import json, sys; print(json.load(sys.stdin)[sys.argv[1]])' "$field" <<<"$payload"
}

wait_for_api() {
  echo "==> Waiting for API health"
  for _ in $(seq 1 90); do
    if curl -sf "${API_BASE}/health" >/dev/null; then
      return 0
    fi
    sleep 2
  done
  echo "API did not become healthy at ${API_BASE}/health" >&2
  return 1
}

wait_for_run() {
  local token="$1"
  local run_id="$2"
  local status=""
  for _ in $(seq 1 90); do
    local body
    body="$(curl -sf -H "Authorization: Bearer ${token}" "${API_BASE}/generation/runs/${run_id}")"
    status="$(json_field "$body" status)"
    if [[ "$status" == "completed" ]]; then
      echo "$body"
      return 0
    fi
    if [[ "$status" == "failed" ]]; then
      echo "Generation run failed: $body" >&2
      return 1
    fi
    sleep 2
  done
  echo "Timed out waiting for run ${run_id} (last status: ${status})" >&2
  return 1
}

echo "==> Phase 1A verification"
SKIP_OLLAMA_PULL=1 make setup
make test

echo "==> Start generate profile (API + worker + Ollama)"
docker compose --profile generate up -d --build

echo "==> Pull smoke model in Ollama container"
for _ in $(seq 1 30); do
  if docker exec assessgen-ollama ollama list >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker exec assessgen-ollama ollama pull "$OLLAMA_MODEL"

wait_for_api

echo "==> Health check"
curl -sf "${API_BASE}/health" | python3 -m json.tool >/dev/null

echo "==> Login"
login_body="$(curl -sf -X POST "${API_BASE}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}")"
token="$(json_field "$login_body" access_token)"

echo "==> Queue smoke generation run"
idem_key="verify-1a-$(date +%s)-$RANDOM"
create_body="$(curl -sf -X POST "${API_BASE}/generation/runs" \
  -H "Authorization: Bearer ${token}" \
  -H "Idempotency-Key: ${idem_key}" \
  -H "Content-Type: application/json" \
  -d '{"module":"smoke","spec":{"kind":"smoke"}}')"
run_id="$(json_field "$create_body" run_id)"
echo "Run queued: ${run_id}"

echo "==> Poll until completed"
wait_for_run "$token" "$run_id" >/dev/null

echo "==> Assert agent_invocations row exists"
invocation_count="$(docker exec assessgen-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
  "SELECT COUNT(*) FROM agent_invocations WHERE run_id = '${run_id}'")"
if [[ "${invocation_count}" -lt 1 ]]; then
  echo "Expected agent_invocations row for run ${run_id}, found ${invocation_count}" >&2
  exit 1
fi
echo "agent_invocations rows: ${invocation_count}"

echo "==> Celery worker restart"
docker restart assessgen-worker >/dev/null
sleep 5

echo "==> Queue second run after worker restart"
idem_key2="verify-1a-restart-$(date +%s)-$RANDOM"
create_body2="$(curl -sf -X POST "${API_BASE}/generation/runs" \
  -H "Authorization: Bearer ${token}" \
  -H "Idempotency-Key: ${idem_key2}" \
  -H "Content-Type: application/json" \
  -d '{"module":"smoke","spec":{"kind":"smoke"}}')"
run_id2="$(json_field "$create_body2" run_id)"
wait_for_run "$token" "$run_id2" >/dev/null

invocation_count2="$(docker exec assessgen-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
  "SELECT COUNT(*) FROM agent_invocations WHERE run_id = '${run_id2}'")"
if [[ "${invocation_count2}" -lt 1 ]]; then
  echo "Expected agent_invocations row after worker restart, found ${invocation_count2}" >&2
  exit 1
fi

echo "Phase 1A verification passed."
