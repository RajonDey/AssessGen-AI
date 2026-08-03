# Phase 1 — Master checklist

Single place to track **Phase 1A → 1D** and [roadmap exit criteria](roadmap.md#phase-1-exit-criteria).
Update this file when a sub-phase completes — do not mark the roadmap exit criteria elsewhere alone.

---

## Sub-phases

| Phase | Plan | Status | Exit verified by |
|-------|------|--------|------------------|
| **1A** Foundation | [phase-1a-foundation.md](phase-1a-foundation.md) | Complete | `make verify-1a` |
| **1B** Reading | [phase-1b-reading.md](phase-1b-reading.md) | Complete (code); live validation ongoing | `make verify-1b` |
| **1C** Thin verticals | [phase-1c-thin-verticals.md](phase-1c-thin-verticals.md) | **In progress** | `make verify-1c` (TBD) |
| **1D** Benchmark | [phase-1d-benchmark.md](phase-1d-benchmark.md) | Not started | `make benchmark` (TBD) |

---

## 1A — Foundation

- [x] Repo, uv, Docker Compose, Alembic schema
- [x] DB triggers (immutability, approval gate)
- [x] Auth, LLM gateway, Celery, LangGraph smoke graph
- [x] structlog, Makefile, import-linter CI

---

## 1B — Reading

- [x] Rule engine + IELTS Reading pack (types 1–5)
- [x] Reading graph (L1–L3 + human review)
- [x] Originality + dedup
- [x] Critic + reviser (max 2 loops)
- [x] Admin: generate, review, bank
- [x] Calibration (synthetic fixtures); authentic fixtures optional
- [ ] Full 3-passage / 40-question live run on target model (operational proof)

---

## 1C — Listening, Writing, Speaking (thin)

### Shared (T0)

- [x] Module dispatch in worker + API (stubs for L/W/S until graphs land)
- [ ] Thin graph pattern (L1 + originality + persist + review)
- [x] Persistence convention documented (`backend/app/modules/ielts/PERSISTENCE.md`)

### Listening

- [x] Schemas, spec, request parser (Sections 1–2)
- [ ] `prompts/` — planner, script generator
- [ ] `R-LIST-001..008` + unit tests
- [ ] Script + item agents + graph + run service
- [ ] End-to-end: generate → review → approve → bank

### Writing

- [ ] Task 2 schemas + five question types
- [ ] `R-WRIT-001..006` + unit tests (006 N/A for Task 2)
- [ ] Task 2 agent + graph + run service
- [ ] End-to-end per question type (or combined run)

### Speaking

- [ ] Part 1 + Part 2 schemas
- [ ] `R-SPK-001..005` + unit tests (004 N/A without Part 3)
- [ ] Agents + graph + run service
- [ ] End-to-end: generate → review → approve → bank

### Admin

- [ ] Module picker on Generate
- [ ] Review display per module

### Verification

- [ ] `make verify-1c` + `scripts/verify-1c.sh`

---

## 1D — Benchmark harness

- [ ] Harness scaffold + result schema
- [ ] Planted-defect suite
- [ ] Runs for `qwen3.5:4b`, `qwen3.5:9b`, `gemma4:12b`
- [ ] Cost/throughput report artefact
- [ ] `make benchmark`

---

## Phase 1 exit criteria (roadmap)

From [roadmap § Phase 1 exit](roadmap.md#phase-1-exit-criteria):

- [ ] All four modules produce reviewable content
- [ ] Reading proven end-to-end through publication
- [x] Rule engine calibrated (synthetic); authentic calibration when corpus ready (Q2)
- [ ] ≥ 100 items human-reviewed; approval rate measured
- [ ] Benchmark harness producing comparable model results
- [ ] Import-linter green; unit coverage ≥ 90% on `domain/`

---

## Deferred to Phase 2+ (do not build during 1C)

| Item | Phase |
|------|-------|
| Critic + reviser for L/W/S | 2 |
| Writing Task 1 + model answers + `R-ANS-*` | 2 |
| Speaking Part 3 + `R-SPK-006+` + sample answers | 2 |
| Listening audio (Kokoro, ASR) | 3 |
| Consumer API / IELTS Ready | 3 |
| Multi-tenant SaaS | 4 |
| Examiner validation (Q1) | Before external sale |

---

## References

- [Execution Roadmap](roadmap.md)
- [Open Questions](open-questions.md)
