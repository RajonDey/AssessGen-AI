# Phase 1D — Benchmark harness (Execution Plan)

> **Status:** In progress — mock + live Reading harness wired; full model matrix run pending.
> **Parent:** [Execution Roadmap](roadmap.md) § 1D.
> **Prerequisite:** [Phase 1C](phase-1c-thin-verticals.md) exit criteria (E2E proof still open).
> **Master tracker:** [Phase 1 checklist](phase-1-checklist.md).

---

## Goal

Produce the **first comparable model report**: rule-gate pass rate, planted-defect detection, and
machine-hours per approved item — for the deferred production-model decision (Open Question Q4).

---

## What 1D delivers

| Component | Scope |
|-----------|-------|
| Harness CLI | `evals/harness/` — run tasks, record results JSON |
| Five benchmark tasks | Including **planted-defect suite** |
| Model matrix | `qwen3.5:4b`, `qwen3.5:9b`, `gemma4:12b` (local Ollama) |
| Report generator | Cost/throughput table → `evals/results/` |
| CI job (optional) | Weekly or manual; not blocking merge in 1D v1 |

---

## Exit criteria

- [x] Harness runs end-to-end from `make benchmark` (or documented script)
- [ ] Results table: pass rate, defect detection rate, wall time per module/task (needs live Ollama run)
- [x] Planted-defect suite documented — ground truth known by construction
- [x] Report committed or generated artefact path documented in README
- [ ] [Phase 1 checklist](phase-1-checklist.md) — 1D items checked
- [ ] Phase 1 exit criteria in [roadmap](roadmap.md) ready for sign-off

---

## Task sequence (placeholder — detail when 1C completes)

```
T1  Harness scaffold + result schema
 └─▶ T2  Planted-defect tasks (Reading-first)
      └─▶ T3  Module tasks (reading, listening, writing, speaking smoke)
           └─▶ T4  Model runner (Ollama profiles, lease-aware)
                └─▶ T5  Report generator + make benchmark
                     └─▶ T6  Document decision checkpoint (Q4 link)
```

---

## Explicitly out of scope for 1D

- Cloud provider benchmarks (gateway stubs only until configured)
- Examiner validation
- Prompt activation golden-set gate (Phase 2)

---

## References

- [LLM Gateway & Local Models](../core/07-llm-gateway-and-local-models.md) — decision rule
- [Testing & QA](../core/09-testing-and-qa.md) — eval harness section
- [Open Questions Q4](open-questions.md#q4--production-model)
