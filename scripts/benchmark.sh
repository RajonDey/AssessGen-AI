#!/usr/bin/env bash
# Phase 1D model benchmark — mock mode by default (no Ollama required).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

MODE="${BENCHMARK_MODE:-mock}"
MODELS="${BENCHMARK_MODELS:-fast,local}"

uv run python -m app.scripts.benchmark --mode "$MODE" --models "$MODELS" "$@"
