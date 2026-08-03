# Phase 1C — Three thin verticals (Execution Plan)

> **Status:** In progress.
> **Parent:** [Execution Roadmap](roadmap.md) § 1C.
> **Prerequisite:** [Phase 1B](phase-1b-reading.md) exit criteria passed (Reading pipeline proven).
> **Next:** [Phase 1D — Benchmark harness](phase-1d-benchmark.md).
> **Master tracker:** [Phase 1 checklist](phase-1-checklist.md).

Phase 1C adds **Listening, Writing, and Speaking** as thin verticals on the same spine Reading
proved. Each module reaches **generate → L1 structural rules → persist → human review**. No new
infrastructure (queues, gateway, checkpointer, review API pattern all reused).

---

## What 1C delivers (and what it does not)

| In scope (1C) | Explicitly deferred |
|---------------|---------------------|
| Listening Sections 1–2 script + items, text-only review | Audio, Kokoro, ASR (Phase 3) |
| Writing Task 2 prompts, all five question types | Task 1, chart renderer, model answers (Phase 2) |
| Speaking Part 1 + Part 2 cue cards | Part 3, sample answers, TTS (Phase 2–3) |
| Structural rules: `R-LIST-001..008`, `R-WRIT-001..006`, `R-SPK-001..005` | `R-WRIT-007..009`, `R-SPK-006..011`, `R-ANS-*`, `R-SANS-*` (Phase 2) |
| L1 quality gate + human `interrupt()` review | Critic + reviser loop for these modules (Phase 2) |
| Originality (8-gram) on generated text | Dedup tuning, calibration on authentic listening scripts (Phase 2) |
| Admin: module picker on Generate, review queue works for all modules | SSE progress (optional polish; see [open questions](open-questions.md)) |
| Module dispatch in worker + API | Consumer API, publications beyond Reading export pattern |

**Thin vertical definition:** content is reviewable by a human and passes structural MUST rules.
Quality depth (critic, reviser, band claims, examiner validation) is Phase 2.

---

## Exit criteria (phase gate)

All must pass before starting Phase 1D:

- [ ] **Listening:** Section 1 or 2 script + at least one completion item generated, reviewed, approved, visible in bank
- [ ] **Writing:** Task 2 prompt generated for each of the five question types (one run each, or one multi-type run)
- [ ] **Speaking:** Part 1 (3 topics × questions) + Part 2 cue card generated, reviewed, approved
- [ ] All `R-LIST-001..008`, `R-WRIT-001..006`, `R-SPK-001..005` implemented with unit tests
- [ ] `make verify-1c` passes (tests + smoke run per module with mocked LLM in CI)
- [ ] Import-linter green; no IELTS logic outside `modules/ielts/`
- [ ] [Phase 1 checklist](phase-1-checklist.md) updated — 1C items checked

---

## Task sequence (do not skip)

```
T0  Shared module spine (dispatch, thin graph pattern, persistence convention)
 └─▶ T1  Listening pack
      └─▶ T2  Writing pack
           └─▶ T3  Speaking pack
                └─▶ T4  Admin UI (module picker + review display)
                     └─▶ T5  verify-1c + docs handoff to 1D
```

Within each pack, order is always: **schemas → rules → agents → graph → run service → tests**.

---

### T0 — Shared module spine

**Goal:** One pattern for all thin verticals; no fourth fork of orchestration code.

**Work:**

1. **`app/modules/base.py`** — extend `ModuleSpec` if needed: module id, graph builder, run service entry, content shape hints.
2. **`generation_worker.py`** — dispatch `listening` | `writing` | `speaking` | `reading` | `smoke`.
3. **`generation_service` / API** — accept `module` + module-specific `spec` (mirror Reading).
4. **Thin graph template** — shared nodes reused from Reading where possible:
   - `generate` → `quality_l1` → `originality` (text) → `persist_content` → `human_review` → `finalize_run`
   - No critic/reviser nodes in 1C graphs.
5. **Persistence convention** — document in code comments:
   - Listening script → `passages` + `passage_versions.body` (transcript JSON or plain text + metadata)
   - Writing Task 2 → `passages` (prompt text as body, metadata: `task`, `question_type`)
   - Speaking → `passages` (structured JSON: part1 + part2 in body or metadata)
   - Items (listening questions) → existing `items` / `item_versions`
6. **`build_initial_*_state` helpers** per module in `workflows/`.
7. **Review queue** — include `module` in run payload; filter optional in API.

**Acceptance:**

- [ ] `POST /api/v1/generation/runs` accepts `module: listening|writing|speaking` with typed spec
- [ ] Worker routes to correct run service
- [ ] Shared human review + persist nodes work with module field set

---

### T1 — Listening (Sections 1–2, text only)

**Reference:** [Listening module](../modules/listening.md) — Phase 1 row in phasing table.

#### T1a — Scaffold

- `modules/ielts/listening/schemas.py` — `ListeningScript`, speakers, turns, transcript body
- `modules/ielts/listening/spec.py` — Section 1–2 bounds, turn counts, question types for 1C
- `modules/ielts/listening/request.py` — parse generation spec (section, topic, accent, question_count)
- `prompts/` — planner, script generator (section 1 dialogue, section 2 monologue)

#### T1b — Rules `R-LIST-001..008`

| Code | Severity | Check (summary) |
|------|----------|-----------------|
| `R-LIST-001` | must | Answers spoken exactly as they must be written (verbatim in transcript) |
| `R-LIST-002` | must | Natural spoken register (heuristic: contractions, question forms; not essay prose) |
| `R-LIST-003` | should | Hesitations / false starts present in S1/S3-style dialogue (S1 in 1C) |
| `R-LIST-004` | must | Speaker labels consistent throughout |
| `R-LIST-005` | must | Answer targets spread across timeline (not clustered in first N turns) |
| `R-LIST-006` | should | Self-correction distractor present where plan expects it (S1) |
| `R-LIST-007` | should | Spellable proper nouns spelled out when needed |
| `R-LIST-008` | must | Numbers/dates in natural spoken form |

One file per rule under `listening/rules/`, unit tests each.

#### T1c — Agents

- Script planner agent
- Script generator agent (structured turns + offsets)
- Question + answer generator (reuse Reading completion rules on **transcript** as body)
- No critic/reviser in 1C

#### T1d — Graph + run service

- `workflows/graphs/listening_graph.py`
- `services/listening_run_service.py`
- Celery task unchanged (module dispatch only)

**Acceptance:**

- [ ] Section 1 script generates with ≥2 speakers and turn offsets
- [ ] At least one `note_completion` or `sentence_completion` item with verbatim key in transcript
- [ ] L1 gate runs `R-LIST-*` + reused `R-COMP-*` / `R-ITEM-*` where applicable
- [ ] Run reaches `awaiting_review`; approve → bank shows script + items

---

### T2 — Writing (Task 2 prompts only)

**Reference:** [Writing module](../modules/writing.md) — Phase 1 row.

#### T2a — Scaffold

- `modules/ielts/writing/schemas.py` — `WritingTask2Prompt`, question type enum
- `modules/ielts/writing/spec.py` — five question types, min word instruction text
- `modules/ielts/writing/request.py`
- `prompts/task2/` — one template per question type (opinion, discussion, problem-solution, adv/disadv, two-part)

#### T2b — Rules `R-WRIT-001..006`

| Code | Severity | Check (summary) |
|------|----------|-----------------|
| `R-WRIT-001` | must | Clear, arguable proposition |
| `R-WRIT-002` | must | Question type answerable as phrased (both views present if discussion, etc.) |
| `R-WRIT-003` | must | Word-count instruction present (≥250 words for Task 2) |
| `R-WRIT-004` | should | Culturally neutral topic |
| `R-WRIT-005` | should | No specialist knowledge required |
| `R-WRIT-006` | must | *(GT Task 1 only — skip in 1C Task 2 runs; rule registered but N/A for Academic Task 2)* |

**Deferred:** `R-WRIT-007..009` (Task 1 Academic chart rules) → Phase 2.

#### T2c — Agents

- Task 2 generator agent (single prompt output per run; batch type optional)

#### T2d — Graph + run service

- `workflows/graphs/writing_graph.py`
- `services/writing_run_service.py`

**Acceptance:**

- [ ] Each of the five Task 2 types generates a valid prompt
- [ ] `R-WRIT-001..005` evaluated; MUST failures block approval
- [ ] Persisted as passage with metadata; review + bank browser shows prompt text
- [ ] **No model answers, no band labels** in 1C output

---

### T3 — Speaking (Part 1 + Part 2)

**Reference:** [Speaking module](../modules/speaking.md) — Phase 1 row.

#### T3a — Scaffold

- `modules/ielts/speaking/schemas.py` — Part1Topic, Part2CueCard
- `modules/ielts/speaking/spec.py` — topic count, bullet count
- `modules/ielts/speaking/request.py`
- `prompts/part1/`, `prompts/part2/`

#### T3b — Rules `R-SPK-001..005`

| Code | Severity | Check (summary) |
|------|----------|-----------------|
| `R-SPK-001` | must | Part 2 has exactly three "you should say" bullets |
| `R-SPK-002` | must | Part 2 ends with "and explain…" prompt |
| `R-SPK-003` | must | Part 1: 3 topics, 3–4 questions each |
| `R-SPK-004` | must | *(Part 3 count — N/A in 1C; skip when Part 3 absent)* |
| `R-SPK-005` | must | Part 2 bullets independent, non-redundant |

**Deferred:** `R-SPK-006..011` (Part 3 linkage, accessibility) → Phase 2.

#### T3c — Agents

- Topic planner (Part 1 topics + Part 2 theme)
- Part 1 generator
- Part 2 cue card generator

#### T3d — Graph + run service

- `workflows/graphs/speaking_graph.py`
- `services/speaking_run_service.py`

**Acceptance:**

- [ ] Part 1 + Part 2 generated in one run
- [ ] Structural MUST rules pass on valid fixtures
- [ ] Review + bank shows structured speaking content
- [ ] **No sample answers, no band labels**

---

### T4 — Admin UI

**Work:**

1. Generate page — module selector (`reading` | `listening` | `writing` | `speaking`) with module-specific form fields.
2. Review page — show module-appropriate summary (script vs prompt vs cue card).
3. Bank — filter or column for `module` if not already present on passages API.

**Acceptance:**

- [ ] Operator can start a Listening / Writing / Speaking run without API curl
- [ ] Review approve/reject works for each module

---

### T5 — Verification + handoff

**Work:**

1. `scripts/verify-1c.sh` — unit tests + integration smoke (mock LLM) per module.
2. `make verify-1c` in root Makefile.
3. Update [Phase 1 checklist](phase-1-checklist.md) — mark 1C complete.
4. Update [roadmap](roadmap.md) status line.

**Acceptance:**

- [ ] `make verify-1c` green in CI
- [ ] All exit criteria at top of this doc checked

---

## Explicitly out of scope for 1C

Do not build these — they belong to Phase 2 or 3:

- Kokoro TTS, audio QA, ASR round-trip (`R-LIST` audio checks)
- Writing Task 1, chart renderer, `R-WRIT-007..009`, model answers, `R-ANS-*`
- Speaking Part 3, `R-SPK-006..011`, sample answers, `R-SANS-*`
- Critic + reviser loops for Listening / Writing / Speaking
- Prompt registry UI, golden-set gate before activation
- Consumer API / IELTS Ready integration
- Benchmark harness (Phase 1D)
- Examiner validation (Open Question Q1)

---

## Estimated effort

| Task | Estimate | Notes |
|------|----------|-------|
| T0 Shared spine | 1–1.5 days | Critical — do first |
| T1 Listening | 2–3 days | Closest to Reading transcript model |
| T2 Writing | 1–1.5 days | Simplest artefact (prompt only) |
| T3 Speaking | 1.5–2 days | Structured JSON, few agents |
| T4 Admin | 1 day | Module picker + display |
| T5 Verification | 0.5 day | |
| **Total** | **~7–9 days** | Solo, focused; after Reading stable |

---

## References

- [Execution Roadmap](roadmap.md)
- [Phase 1 checklist](phase-1-checklist.md)
- [Phase 1D plan](phase-1d-benchmark.md)
- [Listening](../modules/listening.md) · [Writing](../modules/writing.md) · [Speaking](../modules/speaking.md)
- [Quality & Evaluation](../core/08-quality-and-evaluation.md)
- [Folder Structure](../core/06-folder-structure.md)
