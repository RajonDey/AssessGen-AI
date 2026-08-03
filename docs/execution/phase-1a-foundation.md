# Phase 1A — Foundation (Execution Plan)

> **Status:** Complete.
> **Parent:** [Execution Roadmap](roadmap.md) § 1A.
> **Exit criterion:** `make setup` works from a clean clone; a trivial LangGraph runs against Ollama,
> persists an `agent_invocations` row, and survives a Celery worker restart.

Phase 1A builds the **shared spine** — nothing user-visible, no IELTS content, no admin UI. Every
later phase plugs into what is built here.

---

## What 1A delivers

| Component | 1A scope | Deferred to |
|-----------|----------|-------------|
| Repo scaffold + CI + import-linter | ✅ Full | — |
| Docker Compose (`data`, `backend`, `generate` profiles) | ✅ Full | `full` profile (admin) in 1B |
| Alembic schema (core tables) | ✅ Full | `mock_tests`, `publications` in 1B |
| DB triggers (immutability, approval gate) | ✅ Full | — |
| Auth (login, JWT, tenant scoping) | ✅ Minimal | Consumer API keys in Phase 3 |
| LLM gateway (Ollama only) | ✅ Full | Cloud providers when benchmark data exists |
| Celery + 3 queues | ✅ Wired | Real generation tasks in 1B |
| LangGraph + PostgresSaver | ✅ Trivial graph | Reading graph in 1B |
| structlog + `run_id` correlation | ✅ Full | OpenTelemetry in Phase 3 |
| Admin UI | ✗ None | Phase 1B |
| Rule engine / IELTS modules | ✗ None | Phase 1B |
| Quality gate nodes | ✗ None | Phase 1B |

---

## Prerequisites (before Task 1)

- [ ] **Commit planning docs** — `docs/`, `.cursor/rules/`, `.agents/skills/`, `.gitignore`, `README.md`.
- [ ] **Python 3.12 via uv** — not system 3.14. Confirm: `uv python list`.
- [ ] **Docker Desktop** running — Postgres 18 must come from Compose, not Homebrew Postgres 14.
- [ ] **Ollama installed** — will be pulled by `make setup`.
- [ ] **Read** (skim, don't memorise): [Folder Structure](../core/06-folder-structure.md),
  [Dependencies](../core/10-dependencies.md), [Data Model](../core/04-data-model.md),
  [LLM Gateway](../core/07-llm-gateway-and-local-models.md).
- [ ] **LangGraph skills** in `.agents/skills/` — consult before writing orchestration code (v1 LTS,
  not 0.x tutorials).

---

## Task sequence

Tasks are ordered by dependency. Do not skip ahead — later tasks assume earlier ones.

```
T1 Repo scaffold
 └─▶ T2 CI + import-linter
      └─▶ T3 Docker Compose
           └─▶ T4 Alembic schema
                └─▶ T5 DB triggers + integration tests
                     └─▶ T6 Auth
                          └─▶ T7 LLM gateway
                               └─▶ T8 Celery + queues
                                    └─▶ T9 LangGraph + PostgresSaver
                                         └─▶ T10 Observability
                                              └─▶ T11 Makefile + exit verification
```

---

### T1 — Repository scaffold

**Goal:** Empty but correctly shaped backend tree; dependencies locked.

**Work:**

1. Create top-level layout per [Folder Structure](../core/06-folder-structure.md):
   `backend/`, `infra/`, `evals/`, `scripts/`.
2. Initialise `backend/` as a uv project: Python **3.12**, `pyproject.toml` with runtime + dev deps
   from [Dependencies](../core/10-dependencies.md).
   - Base install only — no `sentence-transformers`/torch yet (optional extra).
   - Include: FastAPI, SQLAlchemy 2.0, Alembic, psycopg v3, pgvector, LangGraph + checkpoint-postgres,
     langchain-ollama, Celery, Redis, structlog, argon2-cffi, pyjwt.
3. Create `backend/.python-version` → `3.12`.
4. Create empty package skeleton under `backend/app/` matching layer directories:
   `api/`, `services/`, `workflows/`, `agents/`, `domain/`, `modules/`, `infrastructure/`,
   `schemas/`, `utils/`.
5. Add `backend/app/main.py` (FastAPI factory stub), `config.py` (pydantic-settings), `container.py`.
6. Add `backend/tests/` with `unit/`, `integration/`, `contract/`, `fixtures/`.
7. Run `uv lock` and commit `uv.lock`.

**Acceptance:**

- [ ] `cd backend && uv sync` succeeds on a clean machine.
- [ ] `uv run python -c "import app"` succeeds.
- [ ] Directory layout matches the doc (layers visible in paths).

---

### T2 — CI + import-linter

**Goal:** Layer contract enforced from the first merge.

**Work:**

1. Add `.github/workflows/ci.yml` — lint + unit + integration on push/PR.
2. Configure **ruff** (lint + format) and **mypy** (strict on `domain/` and `modules/`).
3. Add import-linter contracts from [Testing & QA](../core/09-testing-and-qa.md):
   - `layers` — api → services → workflows → agents → domain → infrastructure.
   - `domain-purity` — no I/O imports in `app.domain`.
   - `gateway-monopoly` — no provider SDKs outside `infrastructure/llm/`.
   - `reference-corpus-quarantine` — agents/workflows/modules cannot reach reference-doc repo.
4. Add **pre-commit** config mirroring CI lint steps.
5. Add `pip-audit` job (weekly or on PR — either is fine for 1A).

**Acceptance:**

- [ ] `uv run lint-imports` (or equivalent) passes on the empty skeleton.
- [ ] A deliberate bad import (e.g. `sqlalchemy` in `domain/`) fails CI.
- [ ] CI runs on push without manual steps.

---

### T3 — Docker Compose

**Goal:** Local infra matches production assumptions; memory profiles work on 16 GB.

**Work:**

1. Add `docker-compose.yml` + `infra/compose/` split (base, dev, test).
2. Services:
   - **Postgres 18 + pgvector** — image `pgvector/pgvector:pg18`.
   - **Redis 8** — Celery broker.
   - **MinIO** — local S3-compatible storage.
3. Compose **profiles** (from [Folder Structure](../core/06-folder-structure.md)):

   | Profile | Starts | Use |
   |---------|--------|-----|
   | `data` | Postgres, Redis, MinIO | Migrations, integration tests |
   | `backend` | `data` + API + one Celery worker | Day-to-day dev |
   | `generate` | `backend` + Ollama (large model) | Content runs — **not** with Next.js |

4. Add `.env.example` with all required vars; document in README.
5. Health checks on Postgres and Redis.

**Acceptance:**

- [ ] `docker compose --profile data up -d` starts cleanly.
- [ ] `psql` connects to Postgres 18 with pgvector extension enabled.
- [ ] MinIO console reachable; bucket auto-created or documented.

---

### T4 — Alembic schema (initial migration)

**Goal:** Core tables exist; ORM models mirror the data model doc.

**Work:**

1. Configure Alembic with async SQLAlchemy 2.0 style.
2. First migration creates tables from [Data Model](../core/04-data-model.md):

   **Identity & tenancy:** `organizations`, `users`

   **Provenance:** `generation_runs`, `agent_invocations`, `prompt_versions`

   **Content:** `passages`, `passage_versions`, `items`, `item_versions`

   **Quality & review:** `quality_checks`, `reviews`

   **Vectors:** `embeddings` (pgvector, 768 dimensions, model name on row)

   **Reference (quarantined):** `reference_documents` — schema only; no ingest in 1A

   **Supporting:** `topics`, `tags` (minimal — enough for FK integrity)

3. Omit for now (1B): `question_sets`, `mock_tests`, `publications`, `question_set_items`.
4. SQLAlchemy ORM models in `infrastructure/db/models/`.
5. Repository base class in `infrastructure/db/repositories/base.py` — **requires `organization_id`**
   on every query; missing scope raises.
6. Seed migration or script: one org (`internal`), one admin user.

**Acceptance:**

- [ ] `alembic upgrade head` from empty succeeds.
- [ ] All tables, indexes and FKs match the data model doc.
- [ ] `embeddings.embedding` column is `vector(768)`.
- [ ] Seed org + admin user exist after `make setup`.

---

### T5 — DB triggers + integration tests

**Goal:** Invariants enforced by the database, not discipline.

**Work:**

1. Add triggers/functions per [Data Model](../core/04-data-model.md) § Invariants:

   | Trigger | Behaviour |
   |---------|-----------|
   | Version immutability | `BEFORE UPDATE` on `passage_versions` / `item_versions` → raise |
   | Monotonic versions | `version_no` assigned by trigger, not application |
   | Approval gate | Transition to `approved` rejected when unresolved `must` failures exist |
   | Org denorm | `organization_id` on `passage_versions` set from parent passage |

2. Integration tests via **testcontainers** (Postgres 18 + pgvector):

   ```python
   test_updating_an_item_version_raises()
   test_version_numbers_are_assigned_monotonically()
   test_approving_with_failing_must_rule_is_rejected()
   test_repository_query_without_org_id_raises()
   test_idempotency_key_conflict_returns_original_run()
   ```

3. Migration test: `alembic upgrade head` from empty in CI.

**Acceptance:**

- [ ] All integration tests pass against real Postgres.
- [ ] Attempting `UPDATE passage_versions SET body = 'x'` raises.
- [ ] Approval with failing `must` check is rejected at DB level.

---

### T6 — Auth (minimal)

**Goal:** Admin API is authenticated; tenant scoping works end-to-end.

**Work:**

1. `POST /api/v1/auth/login` — email + password → JWT (pyjwt, not python-jose).
2. Password hashing with **argon2-cffi** (not passlib).
3. `api/deps.py` — `get_current_user`, role check dependency, org scoping.
4. JWT claims: `sub` (user id), `org_id`, `role`, `exp`.
5. Stub routers protected by auth — e.g. `GET /api/v1/health` (public),
   `GET /api/v1/me` (authenticated).
6. RFC 9457 error handlers in `api/errors.py`.

**Acceptance:**

- [ ] Login with seed admin returns a valid JWT.
- [ ] Protected endpoint returns 401 without token.
- [ ] Repository calls without `organization_id` raise (tested in T5).

---

### T7 — LLM gateway

**Goal:** Agents call roles, not models; every call is accounted for.

**Work:**

1. Implement in `infrastructure/llm/` per [LLM Gateway](../core/07-llm-gateway-and-local-models.md):

   | Module | Responsibility |
   |--------|----------------|
   | `gateway.py` | Role resolution, orchestration of steps 1–7 |
   | `lease.py` | Global model semaphore (one large model resident) |
   | `structured.py` | Pydantic schema constraint + repair loop (max 2) |
   | `accounting.py` | Token/latency/cost recording |
   | `providers/ollama.py` | Ollama provider via langchain-ollama |

2. Model profiles in config: `fast`, `local` (default for 1A verification).
3. **`fast` profile for 1A smoke tests** — use `qwen3.5:4b` or smallest available model.
4. Every gateway call writes an `agent_invocations` row (linked to `run_id`).
5. Unit tests: role resolution, lease acquire/release, schema repair loop (mocked provider).

**Acceptance:**

- [ ] No file outside `infrastructure/llm/` imports `langchain_ollama`.
- [ ] `gateway.complete(role="metadata", ...)` resolves to the configured model.
- [ ] Second concurrent large-model request waits on lease (test with mock).
- [ ] Successful call persists `agent_invocations` with `prompt_hash`, `model_name`, tokens.

---

### T8 — Celery + queues

**Goal:** Async job dispatch works; queues split by resource profile.

**Work:**

1. `infrastructure/queue/celery_app.py` — Redis broker, three queues:

   | Queue | Concurrency (dev) | Purpose |
   |-------|-------------------|---------|
   | `q.generate` | 1 | Model-bound graph execution |
   | `q.io` | 4 | Embeddings, exports, webhooks |
   | `q.audio` | 2 | TTS (idle in 1A; wired for Phase 3) |

2. Task routing config — generation tasks → `q.generate`.
3. **Celery must not retry content failures** — only infrastructure errors.
4. Worker starts via Compose `backend` profile.
5. Flower optional, dev-only.

**Acceptance:**

- [ ] Worker connects to Redis and consumes from all three queues.
- [ ] A test task dispatched to `q.io` completes.
- [ ] Worker restart does not lose Redis state (jobs re-queued or idempotent).

---

### T9 — LangGraph + PostgresSaver (trivial graph)

**Goal:** Prove the orchestration stack end-to-end; checkpoint survives restart.

**Work:**

1. Read `.agents/skills/langgraph-persistence/SKILL.md` before coding.
2. `workflows/checkpointer.py` — `PostgresSaver` setup, `"sync"` durability mode.
3. **Trivial graph** (`workflows/graphs/smoke_graph.py`):

   ```
   START → call_metadata_agent → persist_invocation → END
   ```

   - Node calls gateway with `role="metadata"` and a tiny schema (e.g. `{ "greeting": str }`).
   - `thread_id` = `generation_runs.id`.
4. Celery task on `q.generate` that:
   - Creates a `generation_runs` row (`status=queued`).
   - Executes the graph.
   - Updates run status to `completed` (or `failed` with reason).
5. **Restart test:**
   - Start graph → kill worker mid-run → restart worker → graph resumes or fails cleanly with
     checkpoint intact (for smoke graph, mid-run kill is optional; checkpoint existence is required).

**Acceptance:**

- [ ] `POST /api/v1/generation/runs` (stub) queues a smoke run, returns `202`.
- [ ] Run completes; `agent_invocations` row exists.
- [ ] `generation_runs.status` transitions `queued → ... → completed`.
- [ ] LangGraph checkpoint table populated in Postgres.
- [ ] After worker kill + restart, a **paused** run (if tested) can resume from checkpoint.

---

### T10 — Observability

**Goal:** Every log line carries correlation context from run #1.

**Work:**

1. `infrastructure/observability/logging.py` — structlog JSON config.
2. Bind context at API entry: `request_id`, `run_id` (when applicable), `organization_id`.
3. Context propagates to Celery tasks and gateway calls.
4. Log format matches [Observability](../core/12-observability-and-cost.md) example.

**Acceptance:**

- [ ] API request logs include `request_id`.
- [ ] Generation run logs include `run_id` throughout the chain.
- [ ] Logs are valid JSON (parseable by `jq`).

---

### T11 — Makefile + exit verification

**Goal:** One command brings a new developer to a working system.

**Work:**

1. Root `Makefile` per [Folder Structure](../core/06-folder-structure.md):

   ```
   make setup      # uv sync, compose up (data), migrate, seed, pull Ollama models
   make dev        # API + worker (backend profile)
   make generate   # backend + Ollama (generate profile)
   make test       # unit + integration
   make test-unit  # domain only
   make lint       # ruff + mypy + import-linter
   make migrate    # alembic upgrade head
   ```

2. `scripts/setup.sh` — idempotent; safe to re-run.
3. Document Compose profile usage in root `README.md`.
4. **Exit verification script** (`scripts/verify-1a.sh`):

   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   make setup
   make test
   curl -sf http://localhost:8000/api/v1/health
   # Login → queue smoke run → poll until completed → assert invocation row exists
   ```

**Acceptance (phase exit — all must pass):**

- [ ] Fresh clone → `make setup` → no manual steps.
- [ ] `make lint` green.
- [ ] `make test` green (unit + integration).
- [ ] Smoke generation run completes against Ollama (`fast` profile).
- [ ] `agent_invocations` row exists for the smoke run.
- [ ] Celery worker restart during/after a run does not corrupt state.
- [ ] import-linter contracts green.

---

## Explicitly out of scope for 1A

Do not build these — they belong to 1B or later:

- Admin UI (`admin/`)
- Reading / Listening / Writing / Speaking agents and graphs
- Rule engine rules (`R-*`)
- Quality gate nodes (`quality_gate.py`, `human_review.py`, `revision_loop.py`)
- Originality checker / reference corpus ingest
- Critic / reviser loop
- Prompt files under `modules/ielts/`
- OpenAPI client generation (`make gen-client`)
- Benchmark harness (`evals/harness/`)
- Cloud LLM providers (OpenAI, Anthropic, Google)

---

## Estimated effort

| Task | Estimate | Notes |
|------|----------|-------|
| T1 Scaffold | 0.5 day | |
| T2 CI | 0.5 day | import-linter config is fiddly |
| T3 Docker | 0.5 day | |
| T4 Schema | 1 day | Largest single task |
| T5 Triggers | 1 day | Triggers + testcontainers |
| T6 Auth | 0.5 day | |
| T7 Gateway | 1.5 days | Critical path |
| T8 Celery | 0.5 day | |
| T9 LangGraph | 1 day | Read skills first |
| T10 Logging | 0.25 day | |
| T11 Makefile | 0.5 day | |
| **Total** | **~7–8 days** | Solo, focused |

---

## Phase 1A → 1B handoff

When exit criteria pass, start [Phase 1B (Reading)](roadmap.md#1b--reading-end-to-end):

1. Reading agents (planner, passage, question, answer).
2. Rule engine with `R-PASS-*`, `R-ITEM-*`, `R-COMP-*`, `R-HEAD-*`, `R-SET-*`.
3. Full quality loop + `interrupt()` human review.
4. Admin UI (generate + review screens).
5. Calibration against authentic material (requires [Q2](open-questions.md#q2--authentic-material-inventory)).

---

## References

- [Execution Roadmap](roadmap.md)
- [Folder Structure](../core/06-folder-structure.md)
- [Data Model](../core/04-data-model.md)
- [Dependencies](../core/10-dependencies.md)
- [LLM Gateway](../core/07-llm-gateway-and-local-models.md)
- [Testing & QA](../core/09-testing-and-qa.md)
- [API Design](../core/05-api-design.md)
- LangGraph skills: `.agents/skills/langgraph-fundamentals/`, `langgraph-persistence/`
