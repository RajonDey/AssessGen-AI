# Execution Roadmap

> **Status:** Phase *shape* below. **Phase 1A** is complete ([plan](phase-1a-foundation.md)).
> **Phase 1B** is complete in code ([plan](phase-1b-reading.md)).
> **Phase 1C** is in progress ([plan](phase-1c-thin-verticals.md)).
> Track all gates: [Phase 1 checklist](phase-1-checklist.md).

## Sequencing principles

1. **The spine before the modules.** Gateway, schema, orchestrator, rule engine and review UI are
   shared by all four modules. Building them once, properly, is the difference between four modules
   and four forks.
2. **Machine-checkable before judgement-dependent.** Within and across modules, build what we can
   verify first. It is the only way to earn trust in the pipeline before relying on it.
3. **Prove the loop end-to-end early.** One item that travels the entire path — request → generate →
   gate → review → approve → publish → export — teaches more than four modules stuck at generation.
4. **Instrument from run #1.** `agent_invocations` and `quality_checks` cannot be backfilled, and they
   are what the hardware decision depends on.
5. **Calibrate before trusting.** No rule blocks content in anger until it has been measured against
   authentic material.

---

## Phase 1 — Foundation & four thin verticals

**Goal:** the shared spine works, the full quality loop is proven on Reading, and all four modules
generate something reviewable.

You chose breadth over depth for Phase 1. This structure honours that without producing four
half-built pipelines: the *spine* is deep, Reading is deep, and the other three modules reach
generate → store → review depth on the same rails, inheriting the quality loop in Phase 2.

### 1A — Foundation (nothing user-visible)

- Repository, `uv` project, Python 3.12, ruff/mypy/**import-linter** in CI from the first commit
- Docker Compose profiles: Postgres 18 + pgvector, Redis, MinIO
- Alembic schema: organizations, users, runs, invocations, passages, items, versions, quality_checks,
  reviews, embeddings, prompts
- Immutability and approval-gate triggers, **with integration tests**
- Auth: login, JWT, roles, repository-level tenant scoping
- **LLM gateway**: role routing, model lease, structured output + repair, full accounting
- Celery with the three queues; LangGraph `PostgresSaver` wired
- structlog JSON with `run_id` correlation

**Exit:** `make setup` works from a clean clone; a trivial graph runs against Ollama, persists an
invocation record, and survives a worker restart.

### 1B — Reading, end to end

- Planner, passage, question, answer agents (types 1–5: the verbatim-answer and heading types)
- Rule engine: `R-PASS-*`, `R-ITEM-*`, `R-COMP-*`, `R-HEAD-*`, `R-SET-*`
- Originality (8-gram vs corpus) and dedup (pgvector)
- Critic + bounded reviser loop
- `interrupt()` human review, resume via API
- **Calibration run against authentic papers** — this gates everything downstream
- Admin: generate screen, live SSE progress, review screen, bank browser

**Exit:** a 3-passage / 40-question Academic Reading test generated, reviewed, approved, published
and exported. Rule-engine false-positive rate ≤ 5 % on authentic material.

### 1C — Three thin verticals

Reusing the spine, no new infrastructure:

- **Listening:** Section 1–2 script generation, text-only review. **No audio.**
- **Writing:** Task 2 prompt generation across five question types, with review.
- **Speaking:** Part 1 questions and Part 2 cue cards, with review.

Each gets structural rules only (`R-LIST-001..008`, `R-WRIT-001..006`, `R-SPK-001..005`). No sample
answers, no band claims, no TTS.

### 1D — Benchmark harness

- Five benchmark tasks including the **planted-defect suite**
- Run against `qwen3.5:4b`, `qwen3.5:9b`, `gemma4:12b`
- First cost/throughput report

**Exit:** a table comparing local models on rule-gate pass rate, defect detection, and machine-hours
per approved item. The first real evidence for the deferred model decision.

### Phase 1 exit criteria

- [ ] All four modules produce reviewable content
- [ ] Reading proven end-to-end through publication
- [x] Rule engine calibrated, false positives ≤ 5 %
- [ ] ≥ 100 items human-reviewed; approval rate measured
- [ ] Benchmark harness producing comparable model results
- [ ] Import-linter contract green; unit coverage ≥ 90 % on `domain/`

---

## Phase 2 — Quality depth & the review flywheel

**Goal:** the quality loop extends to all modules, and review effort starts falling.

- Extend the full quality loop (critic + reviser) to Listening, Writing, Speaking
- Reading question types 6–9; **True/False/Not Given last**, with a permanent 100 % review rate
- Writing: Task 1 Academic with **structured chart data** + deterministic rendering; model answers
  at Bands 6–9 with evidenced justification and monotonicity checks
- Speaking: Part 3 with two-sided thematic-linkage checks; sample answers
- Prompt management: registry, diff, activate/rollback, **golden-set gate before activation**
- Sampling-based review policy driven by measured approval rates
- Rejection reason-code analytics → rule backlog
- Prometheus metrics; quality dashboard with prompt-version annotations
- Team golden set (100–150 labelled items) with inter-rater agreement recorded

**Exit:** approval rate ≥ 70 % first pass; reviewer minutes per approved item ≤ 3; a prompt change can
be shown to have improved quality with statistical evidence rather than anecdote.

---

## Phase 3 — Audio, assembly & scale

**Goal:** complete four-skill mock tests, produced at volume.

- **Kokoro TTS** for Listening; multi-voice assignment; **ASR round-trip audio QA**
- S3/R2 asset pipeline with signed URLs
- Listening Sections 3–4; map/diagram labelling
- Full mock test builder (drag-and-drop), validation, publication
- Export: PDF, DOCX, JSON
- Consumer API v1 + IELTS Ready integration
- OpenTelemetry tracing; alerting (originality block pages)
- Bulk generation from a topic × band × type matrix
- Speaking TTS: examiner questions, Band 8–9 samples only

**Exit:** a complete four-skill mock test published and consumed by IELTS Ready through the consumer
API. Throughput measured against target volume.

---

## Phase 4 — Multi-tenant SaaS

Only after the engine is demonstrably producing good content at volume. Selling a content engine
whose content is not yet validated would be premature in a way that is hard to recover from.

- Organisation management, roles, invitations
- Postgres row-level security as defence in depth
- API key management, scopes, per-key rate limits, usage metering
- Billing hooks and subscription plans
- White-label theming
- Public API documentation and developer portal
- Question-pack marketplace

---

## Cross-cutting, continuous

These are not phases. They run throughout:

| Activity | Cadence |
|----------|---------|
| Rule additions from rejection reason codes | Continuous |
| Calibration re-run against authentic material | Every rule change |
| Benchmark re-run | Every model or prompt change |
| Dependency audit | Weekly in CI |
| Cost/throughput review | Monthly — informs the hardware decision |

---

## Decision checkpoints

Deliberate stop-and-think moments where evidence should change the plan:

| Checkpoint | When | Question |
|-----------|------|----------|
| **Local model viability** | End of Phase 1 | Is the local model's approval rate within reach of usable? If far off, the plan changes |
| **Hardware vs cloud** | End of Phase 2 | Cost/throughput data now exists — see the decision rule in [LLM Gateway](../core/07-llm-gateway-and-local-models.md) |
| **Examiner validation** | Before any external sale | Are band claims validated? Cannot sell without this |
| **SaaS go/no-go** | End of Phase 3 | Is content quality good enough to sell? Is there external demand? |

The first checkpoint is the one most likely to be uncomfortable. If Phase 1 shows a 9 B model
producing a 40 % approval rate, that is important information arriving as early as it possibly could —
which is exactly what the phase was designed to produce.

---

## What could go wrong, and the early warning

| Risk | Early signal | Response |
|------|-------------|----------|
| Local model too weak | Phase 1 approval rate < 40 % | Escalate the model decision immediately; consider a cloud provider for the generator role only |
| Rule engine too strict | Calibration false positives > 10 % | Halt rule authoring; fix before adding more |
| Review is the bottleneck | Reviewer minutes/item > 5 | Invest in review UX and sampling before generating more volume |
| Scope dilution across four modules | Phase 1B slipping while 1C grows | Freeze 1C; finish Reading. Reading is the reference — without it, the others have no template |
| Memory thrash on the dev machine | `llm.lease.waited` climbing; machine unusable | Drop to the `fast` profile for pipeline work; reserve the 9 B model for content runs |

The scope-dilution row deserves attention because it is the risk introduced by the Phase 1 breadth
decision. The mitigation is specific: **if Reading is not finished, the other three modules stop.**
They exist to prove the spine generalises, not to ship in parallel.
