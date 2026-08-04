# Evals — golden sets, calibration, benchmarks

Offline evaluation assets and harnesses. Nothing here runs in production.

## Layout

```
evals/
├── harness/           Runner, schemas, report writer
├── benchmarks/
│   ├── tasks/         Five fixed tasks (versioned JSON)
│   ├── planted_defects/  Ground-truth defective fixtures (Task 5)
│   └── results/       Generated reports (gitignored except .gitkeep)
└── calibration/       Rule-engine calibration fixtures
```

## Benchmark (Phase 1D)

**Mock mode** (default — no Ollama, suitable for CI):

```bash
make benchmark
# or
BENCHMARK_MODE=mock BENCHMARK_MODELS=fast,local make benchmark
```

**Live mode** (Reading generation via Ollama + Postgres; requires `make dev`):

```bash
BENCHMARK_MODE=live BENCHMARK_MODELS=fast,local,local-hq make benchmark
```

Live mode runs tasks 1–4 through the Reading graph (`dev_mode`, auto-approve) and all
planted-defect fixtures. Expect several minutes per profile on local Ollama.

Reports are written to `evals/benchmarks/results/` as JSON + Markdown.

See [Phase 1D plan](../docs/execution/phase-1d-benchmark.md) and
[LLM Gateway § Benchmark](../docs/core/07-llm-gateway-and-local-models.md).
