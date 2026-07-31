# Phase 1B — Reading, end to end (Execution Plan)

> **Status:** Complete.
> **Parent:** [Execution Roadmap](roadmap.md) § 1B.
> **Prerequisite:** [Phase 1A](phase-1a-foundation.md) exit criteria passed.
> **Exit criterion:** A 3-passage / 40-question Academic Reading test generated, reviewed, approved,
> published and exported; rule-engine false-positive rate ≤ 5 % on authentic material.

---

## What 1B delivers

| Component | Scope |
|-----------|-------|
| Domain rule engine | `protocol`, `registry`, `report` — pure Python, no I/O |
| IELTS Reading pack | Schemas (types 1–5), spec, rules, prompts, graph |
| Reading agents | Planner, passage, question, answer, critic, reviser |
| Quality nodes | L0–L2 gate, critic loop, `interrupt()` human review |
| Originality + dedup | 8-gram checker, pgvector similarity |
| Admin UI | Generate (SSE), review, bank browser |
| Calibration | Run against authentic papers before rules may block |

**Phase 1 target question types:** sentence completion, summary completion, short answer,
note/table completion, matching headings (types 1–5).

---

## Task sequence

```
T1  Rule engine (domain/quality)
 └─▶ T2  IELTS Reading scaffold (schemas, spec, module layout)
      └─▶ T3  Passage rules R-PASS-001..009 + unit tests
           └─▶ T4  Item + completion rules R-ITEM-*, R-COMP-*, R-HEAD-*, R-SET-*
                └─▶ T5  Reading agents (planner → answer)
                     └─▶ T6  reading_graph + quality_gate / revision_loop nodes
                          └─▶ T7  Originality checker + dedup
                               └─▶ T8  Critic + reviser loop
                                    └─▶ T9  Human review interrupt + review API
                                         └─▶ T10 Admin UI (generate + review)
                                              └─▶ T11 Calibration + exit verification
```

Do not skip ahead — the graph assumes rules and schemas exist.

---

### T1 — Rule engine

**Goal:** Deterministic L1 gate infrastructure in `app/domain/quality/`.

**Work:**

1. `protocol.py` — `Rule` protocol, `RuleResult` model (per quality doc).
2. `registry.py` — register rules by code, run all, filter by severity.
3. `report.py` — aggregate results; `has_blocking_failures`, no headline score.

**Acceptance:**

- [ ] `RuleResult` matches doc schema (`rule_code`, `passed`, `severity`, `message`, `detail`).
- [ ] Registry runs rules in stable order; `must` failures block approval.
- [ ] Unit tests for registry aggregation.

---

### T2 — IELTS Reading scaffold

**Goal:** Module pack layout and Pydantic schemas for types 1–5.

**Work:**

1. `modules/ielts/spec.py` — exam timings, Academic Reading structure.
2. `modules/ielts/reading/schemas.py` — passage, item, answer key, evidence shapes.
3. `modules/ielts/reading/spec.py` — word-count bounds, question counts, type list.

**Acceptance:**

- [ ] Schemas validate example payloads from [Reading module doc](../modules/reading.md).
- [ ] No IELTS logic leaks outside `modules/ielts/`.

---

### T3 — Passage rules

**Goal:** `R-PASS-001` through `R-PASS-009` implemented, one file per rule.

**Acceptance:**

- [x] Each rule has a paired unit test with pass and fail fixtures.
- [x] Rules import only from `domain/` and stdlib — no I/O.

---

### T4 — Item and set rules

**Goal:** `R-ITEM-*`, `R-COMP-*`, `R-HEAD-*`, `R-SET-*` for types 1–5.

**Acceptance:**

- [x] Each rule has unit tests with pass and fail fixtures.
- [x] Item, completion, heading, and set registries wired in `rules/__init__.py`.

---

### T5 — Reading agents

**Goal:** Stateless agents calling gateway roles; typed in/out.

**Work:**

1. `agent_schemas.py` — planner, passage, question, and answer I/O models.
2. `prompts/` — versioned templates for planner, passage, questions, answers.
3. Agents: planner, passage generator, passage adaptor (Mode B), question generator, answer generator.
4. `PassageSourceMode` enum for generated / ingested / adapted pipeline fork (T6).

**Acceptance:**

- [x] Each agent calls `LLMGateway.complete` with a role (never a model name).
- [x] Every call is schema-constrained (Pydantic output).
- [x] Prompts live as files, not inline strings.
- [x] Unit tests mock the gateway; no model calls in pytest.

---

### T6 — Reading graph

**Goal:** Full pipeline per [Reading pipeline](../modules/reading.md); PostgresSaver checkpoints.

**Work:**

1. `workflows/graphs/reading_graph.py` — planner → passage fork → L1 gates → items.
2. `workflows/nodes/reading_quality.py` — passage, item, and set rule evaluation.
3. `services/reading_run_service.py` — Celery entry with request parsing; L2 wiring via `services/reading_quality.py`.
4. Module dispatch in `services/generation_worker.py` (`smoke` | `reading`); Celery task name unchanged.
5. Mode B fork: `generated` / `adapted` / `ingested` passage paths.

**Acceptance:**

- [x] Graph runs planner → passage → question → answer → L1 quality gates.
- [x] Bounded replan (max 2) and passage regeneration (max 2) loops.
- [x] PostgresSaver checkpoints via `durability="sync"`.
- [x] Integration test completes end-to-end with mocked LLM.

---

### T7 — Originality + dedup

**Goal:** 8-gram overlap (hard block), embedding dedup (reference corpus quarantine applies).

**Work:**

1. `domain/quality/common/ngrams.py` — normalize, 8-gram shingles, overlap detection.
2. `infrastructure/originality/checker.py` — reference corpus consumer (quarantine enforced).
3. `infrastructure/vector/dedup.py` — pgvector similarity against our content bank.
4. `LLMGateway.embed()` — embedding role for dedup vectors.
5. L2 nodes wired into reading graph after L1 passage quality.

**Acceptance:**

- [x] 8-gram match against `reference_documents` hard-blocks with no override.
- [x] Ingested/adapted mode permits overlap with declared source text.
- [x] Dedup rejects passages above configured cosine similarity threshold.
- [x] `reference_documents` repository import quarantine preserved.

---

### T8 — Critic + reviser

**Goal:** Structured findings only; max 2 revision loops.

**Work:**

1. `domain/quality/critic.py` — `CriticFinding`, `CriticOutput` (no score field).
2. `modules/ielts/reading/agents/critic.py` and `reviser.py` with versioned prompts.
3. Graph nodes `run_critic`, `run_reviser` after L1 item quality; bounded revision loop.
4. L1 `must` failures route to reviser before critic; critic `must` findings route to reviser.

**Acceptance:**

- [x] Critic uses `LLMRole.CRITIC` and sees passage + items only.
- [x] `CriticOutput` has findings only — no overall score.
- [x] Revision loops hard-capped at 2 (`MAX_REVISION_ATTEMPTS`).
- [x] Mocked integration test covers critic → persist path.

---

### T9 — Human review

**Goal:** LangGraph `interrupt()`; resume via review API.

**Work:**

1. `workflows/nodes/persist_content.py` — passage/item versions before review.
2. `workflows/nodes/human_review.py` — `interrupt()` with review payload.
3. Run status `awaiting_review`; resume via `POST /api/v1/generation/runs/{id}/resume`.
4. `GET /api/v1/review/queue` — list runs awaiting review.

**Acceptance:**

- [x] Graph pauses at human review with persisted content IDs in interrupt payload.
- [x] Resume with `{"decision": "approve"}` completes the run.
- [x] Resume with reject fails the run with reason attached.
- [x] Review queue endpoint returns awaiting-review runs.

---

### T10 — Admin UI

**Goal:** Next.js 16 app — login, generate (SSE), review screen, bank browser.

**Login scope (internal v1 — keep minimal):**

- Single email + password form → existing `POST /api/v1/auth/login` → JWT in memory/`localStorage`.
- Route guard only; no OAuth, MFA, signup, password reset, or refresh-token UX.
- Product-grade auth (SSO, session hardening, etc.) deferred to a later productisation phase.

**Work:**

1. `admin/` Next.js app with `/login`, `/generate`, `/review`, `/bank`.
2. Minimal bank APIs: `GET /api/v1/passages`, `GET /api/v1/items`.
3. Generate page polls run status (SSE deferred; polling is sufficient for internal v1).
4. Review page uses queue + resume API.

**Acceptance:**

- [x] Login with seeded admin user (`admin@assessgen.local` / `admin`).
- [x] Start a reading generation run and observe status updates.
- [x] Approve/reject awaiting-review runs from the review screen.
- [x] Browse persisted passages and items in the bank.

**Run locally:**

```bash
make dev          # API + worker (backend profile)
make admin-dev    # http://localhost:3000
```

---

### T11 — Calibration + exit verification

**Goal:** False-positive rate ≤ 5 % on authentic material; full test publish/export.

**Work:**

1. `modules/ielts/reading/calibration.py` — run MUST rules against fixtures.
2. `app/scripts/calibrate_reading.py` + `make calibrate`.
3. `GET /api/v1/quality/reports/calibration`.
4. Approve on human review; `POST /api/v1/exports/reading` JSON export + publish.
5. `scripts/verify-1b.sh` — tests + calibration gate.

**Acceptance:**

- [x] Built-in synthetic fixtures pass with 0 % false-positive rate.
- [x] `make calibrate` exits 0 when rate ≤ 5 %.
- [x] Calibration report API returns fixture count, rate, and failures.
- [x] Approve sets passage/items to `approved`; export marks `published`.
- [x] `make verify-1b` runs tests and calibration.

**Run locally:**

```bash
make calibrate
make verify-1b
```

Place authentic paper fixtures (gitignored) under `evals/calibration/authentic/reading/*.json`
to measure false positives against real IELTS material.

## Explicitly out of scope for 1B

- Listening, Writing, Speaking modules (Phase 1C)
- Question types 6–12 (Phase 2)
- Cloud LLM providers
- Consumer API / IELTS Ready integration (Phase 3)

---

## References

- [Reading module](../modules/reading.md)
- [Quality & Evaluation](../core/08-quality-and-evaluation.md)
- [ADR-0002 Quality gate ordering](../decisions/ADR-0002-quality-gate-ordering.md)
