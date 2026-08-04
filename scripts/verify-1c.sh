#!/usr/bin/env bash
# Phase 1C exit verification — unit/integration tests for thin verticals + admin build.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Phase 1C verification"

echo "==> Backend unit tests"
cd "$ROOT/backend"
uv run pytest tests/unit -q

echo "==> Phase 1C integration graphs (mock LLM)"
uv run pytest \
  tests/integration/test_listening_graph.py \
  tests/integration/test_writing_graph.py \
  tests/integration/test_speaking_graph.py \
  -q

echo "==> Admin build"
cd "$ROOT/admin"
npm run build

echo "Phase 1C verification passed."
