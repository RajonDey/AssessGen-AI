# Evals harness (lightweight)

Validates skills/rules against:

1. Pattern samples in `docs/question/*.json`
2. Planted defects in `evals/fixtures/planted/`

```bash
make eval
# or
cd backend && uv run python evals_runner.py
```

Live LLM generation evals are optional later (`BENCHMARK_MODE=live`). Structural
harness is the regression gate for Phase 1–3 skills and rules.
