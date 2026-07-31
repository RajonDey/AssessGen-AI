#!/usr/bin/env bash
# Run Reading rule-engine calibration against committed and local authentic fixtures.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"
uv run python -m app.scripts.calibrate_reading "$@"
