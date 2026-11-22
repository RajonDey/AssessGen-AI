# 06 — Folder Structure

## Top level

```
assessgen-ai/
├── backend/                 FastAPI app, agents, workers, domain logic
├── admin/                   Next.js 16 admin dashboard
├── infra/                   Docker Compose, Dockerfiles, deployment
├── docs/                    These documents
├── evals/                   Golden sets, benchmark harness, calibration data
├── scripts/                 One-off operational scripts
├── .cursor/rules/           AI agent rules (MDC)
├── .agents/skills/          Installed agent skills (LangChain official)
├── .github/workflows/       CI
├── docker-compose.yml
├── Makefile                 The single entry point for every common task
└── README.md
```

Two deployables (`backend`, `admin`) — not a microservice fleet. `evals/` sits at the top level
because it is a first-class product asset, not test scaffolding: it holds the calibration data that
lets us make quality claims.

---

## Backend

The layer numbering from [System Architecture](02-system-architecture.md) maps directly onto
directories, so a misplaced import is visible in the path itself.

```
backend/
├── pyproject.toml
├── uv.lock
├── .python-version                    # 3.12
├── alembic.ini
├── migrations/versions/
│
├── app/
│   ├── main.py                        # FastAPI factory, lifespan, middleware
│   ├── config.py                      # pydantic-settings; the ONLY place env is read
│   ├── container.py                   # dependency wiring
│   │
│   ├── api/                           # ── L6 INTERFACE ────────────────────
│   │   ├── deps.py                    # auth, pagination, tenant scoping
│   │   ├── errors.py                  # RFC 9457 handlers
│   │   ├── v1/
│   │   │   ├── generation.py  items.py  passages.py  quality.py
│   │   │   ├── review.py  tests.py  publications.py  prompts.py
│   │   │   ├── models.py  analytics.py  auth.py
│   │   └── consumer/v1/
│   │       ├── publications.py  assets.py
│   │
│   ├── services/                      # ── L5 APPLICATION ──────────────────
│   │   ├── generation_service.py      # validate → persist run → dispatch
│   │   ├── review_service.py          # decisions, queue claiming, resume
│   │   ├── publishing_service.py      # snapshot freezing
│   │   ├── quality_service.py         # gate execution & reporting
│   │   ├── test_builder_service.py
│   │   └── export_service.py
│   │
│   ├── workflows/                     # ── L4 ORCHESTRATION ────────────────
│   │   ├── state.py                   # shared graph state types
│   │   ├── checkpointer.py            # PostgresSaver setup
│   │   ├── nodes/                     # reusable nodes shared across modules
│   │   │   ├── quality_gate.py  human_review.py  revision_loop.py
│   │   └── graphs/
│   │       ├── reading_graph.py  listening_graph.py
│   │       ├── writing_graph.py  speaking_graph.py
│   │
│   ├── content/                       # paper shaping used by the live API
│   │   ├── paper_spec.py              # topics, type_plan, SPEC-* checks
│   │   ├── reading_numbering.py       # Academic 1–40 across three passages
│   │   ├── reading_normalize.py       # align sections[] + answer_key
│   │   ├── listening_normalize.py     # fix script/question drift before rules + TTS
│   │   ├── listening_skeleton.py
│   │   ├── listening_brief.py  writing_brief.py
│   │   ├── originality.py  validate.py
│   │   └── cost_ledger.py             # in-process LLM call counts
│   │
│   ├── agents/                        # ── L3 AGENTS ───────────────────────
│   │   ├── base.py                    # Agent[TIn, TOut] contract + tracing
│   │   ├── planner.py
│   │   ├── passage_generator.py
│   │   ├── question_generator.py
│   │   ├── answer_generator.py
│   │   ├── critic.py
│   │   ├── reviser.py
│   │   └── metadata_agent.py
│   │
│   ├── domain/                        # ── L2 DOMAIN — PURE PYTHON, NO I/O ─
│   │   ├── entities/                  # item.py passage.py test.py run.py
│   │   ├── enums.py                   # ItemStatus, Module, ItemType, Severity
│   │   ├── lifecycle.py               # state machine + legal transitions
│   │   ├── quality/
│   │   │   ├── registry.py            # rule discovery & execution
│   │   │   ├── protocol.py            # Rule protocol; RuleResult
│   │   │   ├── common/                # readability.py cefr.py similarity.py text.py
│   │   │   └── report.py              # aggregation, NOT a headline score
│   │   └── scoring.py                 # difficulty & band estimation
│   │
│   ├── modules/                       # ── EXAM PACKS (the extension point) ─
│   │   ├── base.py                    # ModuleSpec protocol every pack implements
│   │   └── ielts/
│   │       ├── spec.py                # timings, section structure, band descriptors
│   │       ├── reading/
│   │       │   ├── schemas.py         # Pydantic item shapes per question type
│   │       │   ├── rules/             # R-READ-001.py … one file per rule
│   │       │   ├── prompts/           # v1/ v2/ — versioned templates
│   │       │   └── graph.py
│   │       ├── listening/  writing/  speaking/
│   │
│   ├── infrastructure/                # ── L1 INFRASTRUCTURE ───────────────
│   │   ├── llm/
│   │   │   ├── gateway.py             # THE choke point — role-based routing
│   │   │   ├── lease.py               # global model semaphore (16 GB guard)
│   │   │   ├── structured.py          # schema-constrained output + repair loop
│   │   │   ├── accounting.py          # tokens, latency, tok/s, cost
│   │   │   └── providers/             # ollama.py openai.py anthropic.py google.py
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   ├── models/                # SQLAlchemy ORM
│   │   │   └── repositories/          # base.py (tenant scoping) + one per aggregate
│   │   ├── vector/embeddings.py  similarity.py
│   │   ├── storage/                   # s3.py (S3/R2), local.py
│   │   ├── tts/kokoro.py  audio_qa.py
│   │   ├── queue/celery_app.py  tasks/
│   │   └── observability/logging.py  tracing.py  metrics.py
│   │
│   ├── schemas/                       # API request/response DTOs (≠ domain entities)
│   └── utils/
│
└── tests/
    ├── unit/                          # domain + rules; no I/O; the bulk of the suite
    ├── integration/                   # testcontainers Postgres+pgvector
    ├── contract/                      # OpenAPI conformance
    ├── e2e/                           # full generation run against a tiny local model
    └── fixtures/
```

### Why `modules/` is separated from `domain/`

`domain/` holds what is true of *all* assessment content: versioning, lifecycle, readability,
similarity. `modules/` holds what is true of *IELTS specifically*: that Academic Reading has three
passages, that completion answers obey a word limit, that Speaking Part 2 has a one-minute prep.

The test of the boundary: **adding TOEFL should create exactly one new directory under `modules/` and
change nothing else.** If TOEFL forces an edit inside `domain/`, `workflows/nodes/`, `infrastructure/`
or `api/`, the abstraction leaked and should be fixed rather than patched.

### Why one file per rule

`modules/ielts/reading/rules/R-READ-001.py` looks fussy until the rule engine has sixty rules. It
buys: a stable code you can reference from a database row, an error message and a document; a test
file that pairs one-to-one; a git history per rule; and painless enable/disable. Rules are the
system's most valuable and most frequently edited asset — they get first-class file structure.

---

## Prompt directory layout

```
modules/ielts/reading/prompts/
├── passage/
│   ├── v1/academic.md   general.md
│   ├── v2/academic.md
│   └── meta.yaml         # active version, params, model hint, changelog
├── questions/
│   ├── v1/mcq_single.md  true_false_notgiven.md  heading_match.md
│   └── meta.yaml
├── answers/v1/...
└── critic/v1/...
```

Prompts are **files under version control**, mirrored into `prompt_versions` for FK integrity and
dashboard rollback. They get diffs, code review, blame and CI evaluation. A prompt change is a code
change, because it changes behaviour exactly as much as code does.

---

## Admin dashboard

```
admin/
├── package.json  next.config.ts  tailwind.config.ts
├── src/
│   ├── app/
│   │   ├── (auth)/login/
│   │   └── (dashboard)/
│   │       ├── generate/            # request + batch matrix + live SSE progress
│   │       ├── review/              # THE most important screen
│   │       ├── bank/                # search, filter, inspect, version history
│   │       ├── tests/               # builder + publish
│   │       ├── quality/             # rule reports, coverage, calibration
│   │       ├── prompts/             # registry, diff, activate, eval results
│   │       └── analytics/           # cost, throughput, reviewer stats
│   ├── components/
│   │   ├── items/                   # type registry → renderer per item_type
│   │   ├── review/                  # side-by-side passage + item + findings
│   │   └── ui/                      # shadcn primitives
│   ├── lib/
│   │   ├── api/generated/           # GENERATED from OpenAPI — never hand-edited
│   │   ├── api/client.ts
│   │   └── hooks/
│   └── types/
└── tests/  e2e/
```

**The review screen is the product.** Everything else is scaffolding around the one workflow that
consumes scarce human attention. It gets the most design effort: passage and item side by side,
quality findings inline with the text they refer to, evidence spans highlighted in the passage, and
keyboard-first approve/reject so a reviewer never touches the mouse.

`lib/api/generated/` is produced by `make gen-client` from the backend's OpenAPI schema. A CI job
regenerates it and fails if the checked-in version is stale, so the client cannot silently drift from
the server.

---

## Evals

```
evals/
├── golden/
│   ├── reading/items.jsonl          # human-labelled items + expected verdicts
│   └── manifest.yaml                # provenance & labelling protocol
├── calibration/
│   ├── authentic/                   # ⚠️ gitignored — licensed material, never committed
│   └── results/                     # rule-engine false-positive reports over time
├── benchmarks/
│   ├── tasks/                       # identical tasks run against every candidate model
│   └── results/                     # per-model quality/latency/cost — server-purchase evidence
└── harness/                         # runner, scorers, report generation
```

`calibration/authentic/` is **gitignored and encrypted at rest**. Licensed third-party material never
enters version control. See [Compliance](11-security-copyright-compliance.md).

---

## Infra

```
infra/
├── docker/               backend.Dockerfile  worker.Dockerfile  admin.Dockerfile
├── compose/              base.yml  dev.yml  test.yml
└── deploy/               (Phase 3+)
```

Compose profiles exist because of the 16 GB constraint — you start only what a task needs:

| Profile | Starts | Approx. memory |
|---------|--------|---------------|
| `data` | Postgres + Redis + MinIO | ~0.6 GB |
| `backend` | `data` + API + one worker | ~1.2 GB |
| `full` | `backend` + admin dev server | ~2.0 GB |
| `generate` | `backend` + Ollama with the large model | ~11.5 GB |

`full` and `generate` are not intended to run simultaneously on this machine.

---

## Naming and file conventions

| Thing | Convention | Example |
|-------|-----------|---------|
| Python modules | `snake_case` | `question_generator.py` |
| Rule files | `R-<MODULE>-<NNN>.py` | `R-READ-001.py` |
| Prompt files | `<purpose>/<version>/<variant>.md` | `passage/v2/academic.md` |
| Migrations | `<rev>_<verb>_<subject>.py` | `a3f1_add_quality_checks.py` |
| React components | `PascalCase.tsx` | `ReviewPanel.tsx` |
| Tests | mirror source path | `tests/unit/domain/quality/test_R_READ_001.py` |

## The Makefile is the interface

Every routine task has a `make` target so nobody needs to remember a compose incantation:

```
make setup           install deps, pull models, start data services, migrate, seed
make dev             API + worker (data profile)
make dev-full        + admin dashboard
make generate        start the generation profile (large model)
make test            unit + integration
make test-unit       fast: domain + rules only
make lint            ruff + mypy + import-linter
make gen-client      regenerate the TypeScript API client from OpenAPI
make migrate         alembic upgrade head
make calibrate       run the rule engine against authentic material
make bench           run the model benchmark harness
```

`make lint` running import-linter is what mechanically enforces the layer contract. Without it, the
architecture in document 02 is a suggestion that decays over a few months.
