#!/usr/bin/env bash
# Phase 1B exit verification — unit/integration tests + rule calibration.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Phase 1B verification"
make test
make calibrate

echo "Phase 1B verification passed."
