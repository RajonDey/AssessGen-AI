# 03 — Technology Stack (Confirmed)

All versions below were **verified against live package registries on 2026-07-30**, not recalled from
memory. Where a proposed choice was changed, the reason is given.

## Verdict on the original proposal

| Proposed | Verdict | Note |
|----------|---------|------|
| Python + FastAPI + SQLAlchemy + Alembic + Pydantic | ✅ Confirmed | Correct choice for this workload |
| LangGraph + LangChain | ✅ Confirmed, with a version warning | Both are on **v1 LTS**. 0.x tutorials will mislead you |
| PostgreSQL | ✅ Confirmed → **pin to 18** | |
| pgvector | ✅ Confirmed | Same DB as content; avoids a sync problem |
| S3 / Cloudflare R2 | ✅ Confirmed | R2 recommended (no egress fees) |
| Celery + Redis | ✅ Confirmed, with a scoped role | Must not overlap LangGraph's retry semantics |
| LiteLLM ("optional") | ⚠️ **Changed** | We write a thin internal gateway instead — see below |
| OpenAI / Gemini / Claude | ⏸️ Deferred | Provider-agnostic gateway; decision deferred pending benchmark data |
| Separate `frontend/` and `admin-dashboard/` | ⚠️ **Changed** | Merged into one Next.js app |

---

## Backend

| Component | Version | Rationale |
|-----------|---------|-----------|
| **Python** | **3.12** | LangChain 1.0 requires ≥ 3.10. 3.12 is the mature choice: full C-extension wheel coverage. **Not 3.14** — despite being installed locally, ML/NLP wheels (spaCy, sentence-transformers, torch) lag on brand-new majors |
| **uv** | 0.11.8 (installed) | Package + venv manager. 10–100× faster than pip; lockfile is reproducible |
| **FastAPI** | 0.141.1 | Async, Pydantic-native, OpenAPI for free |
| **Pydantic** | 2.13.4 | Doubles as the L0 quality gate — the schema *is* the first validation layer |
| **pydantic-settings** | 2.14.2 | Typed config from env |
| **SQLAlchemy** | 2.0.51 | 2.0 typed style only. No legacy Query API |
| **Alembic** | 1.18.5 | Migrations. Every schema change, no exceptions |
| **psycopg** | 3.3.4 | Postgres driver (v3, async-capable). Not psycopg2 |
| **Celery** | 5.6.3 | Job queue |
| **redis-py** | 8.1.0 | Broker/cache client |
| **structlog** | 26.1.0 | Structured JSON logs, correlation IDs |

> **Python version discipline:** the local machine has 3.14.6. The project pins **3.12** via
> `.python-version` and `uv`. Do not develop against the system Python.

## AI / orchestration

| Component | Version | Rationale |
|-----------|---------|-----------|
| **langgraph** | `>=1.0,<2.0` (1.2.10) | Graph orchestration, durable state, `interrupt()` for human approval |
| **langgraph-checkpoint-postgres** | 3.1.0 | `PostgresSaver` — paused runs survive restarts |
| **langchain** | `>=1.0,<2.0` (1.3.14) | Message/tool abstractions |
| **langchain-core** | `>=1.0,<2.0` (1.5.2) | Peer dependency — **install explicitly** |
| **langchain-ollama** | 1.1.0 | Local model provider |
| **langsmith** | 0.10.12 | Tracing + eval datasets. Self-hostable; optional at first |

> ⚠️ **The single biggest correctness trap in this project.** LangChain and LangGraph both shipped v1
> LTS. The overwhelming majority of blog posts, Stack Overflow answers and LLM training data describe
> **0.x** APIs. Symptoms include `interrupt_before=` compile-time hooks (superseded by the runtime
> `interrupt()`), old import paths, and deprecated agent constructors.
>
> **Mitigation:** the official LangChain skills are installed in `.agents/skills/`
> (`langgraph-fundamentals`, `langgraph-persistence`, `langgraph-human-in-the-loop`,
> `langchain-fundamentals`, `langchain-middleware`, `langchain-dependencies`, `eval-engineering`).
> Consult them before writing orchestration code. A Cursor rule enforces this.

### Why not LiteLLM

LiteLLM (1.94.0) is good software and solves a real problem — but it solves ~60 % of ours and we would
still write the other 40 % ourselves:

| We need | LiteLLM gives us |
|---------|-----------------|
| Role-based routing (`generator`/`critic`/`metadata`) | Model-name routing |
| **Global model-lease semaphore** for a 16 GB box | ✗ Nothing equivalent |
| Provenance capture (seed, prompt hash, model digest) written to *our* schema | Partial, own format |
| Schema-constrained output with a repair loop | Partial |
| Local-first accounting in wall-time and tokens/sec | Cost accounting assumes paid APIs |

A thin internal gateway (~300 lines) over `langchain-ollama` and, later, official provider packages
gives us exactly what we need and a dependency we fully understand at the most critical choke point in
the system. **Revisit if** we end up supporting more than four providers or need production
load-balancing across endpoints — recorded in [ADR-0004](../decisions/ADR-0004-llm-gateway.md).

## Data

| Component | Version | Rationale |
|-----------|---------|-----------|
| **PostgreSQL** | **18** | Docker image `pgvector/pgvector:pg18` |
| **pgvector** | **0.8.6** | Bundled in that image. HNSW indexing |
| **Redis** | 8.x | `redis:8-alpine` |

Local Postgres is 14.18 via Homebrew — **do not use it**. The project runs Postgres in Docker so the
version, extensions and locale match production exactly.

**Embedding model and dimensions.** pgvector requires a fixed dimension per column. Default is
`nomic-embed-text` (768 dims), chosen for a small memory footprint alongside a 9 B generator. Changing
embedding model requires a migration and a re-embed backfill — the embedding model name is stored on
every row so a mixed-model state is detectable rather than silently corrupting similarity search.

## NLP & quality tooling

These power the deterministic rule engine — the layer that produces trustworthy signal.

| Component | Version | Used for |
|-----------|---------|----------|
| **textstat** | 0.7.13 | Flesch-Kincaid, Gunning Fog → readability banding |
| **spaCy** | 3.8.14 | Tokenisation, POS, sentence segmentation, NER |
| **wordfreq** | 3.1.1 | Vocabulary frequency → CEFR band proxy |
| **rapidfuzz** | 3.14.5 | Fuzzy near-duplicate stem detection |
| **datasketch** | 2.0.0 | MinHash/LSH for corpus-scale overlap checks |
| **sentence-transformers** | 5.6.1 | Local embeddings if Ollama embedding is insufficient |

## Audio (Listening)

| Component | Version | Rationale |
|-----------|---------|-----------|
| **Kokoro** | 0.9.4 | **Apache 2.0** — commercially usable. 82 M params, CPU-capable, 8 British English voices |
| **soundfile** | 0.14.0 | Audio I/O |
| **espeak-ng** | system pkg | Kokoro's phonemiser backend |

**Rejected: XTTS v2.** Superior voice cloning, but ships under the Coqui Public Model License — 
non-commercial only — and Coqui is defunct, so no commercial licence can be purchased. It is a legal
dead end for a product. **Chatterbox** (MIT) is the fallback if voice cloning becomes a requirement.

## Frontend (Admin Dashboard)

Confirming your question — yes: **Python + FastAPI backend, Next.js frontend** is the right split. The
backend does async orchestration, Postgres and the Python ML/NLP ecosystem, which is exactly where
Python is strongest. The dashboard is a rich interactive review tool, which is exactly where React is
strongest. They talk over the versioned REST API — the same API IELTS Ready will use, which means we
dogfood our own contract from day one.

| Component | Version | Rationale |
|-----------|---------|-----------|
| **Next.js** | 16.2.12 | App Router; server components for heavy list views |
| **React** | 19.2.8 | |
| **TypeScript** | 5.x | **Not 7.0** initially — verify ecosystem readiness before adopting |
| **Tailwind CSS** | 4.3.3 | |
| **TanStack Query** | 5.101.4 | Server-state, caching, optimistic review actions |
| **Zod** | 4.4.3 | Runtime validation of API responses |
| **shadcn/ui** | latest | Accessible primitives, owned source, no lock-in |

**One app, not two.** The original outline had `frontend/` and `admin-dashboard/` as separate
projects. There is one internal audience and one API; two apps would duplicate the client, types and
auth for no benefit. If a public marketing site is ever needed it can be a separate, trivially simple
project.

**Types are generated, not written.** The OpenAPI schema produced by FastAPI generates the TypeScript
client. Hand-written API types drift and then lie.

## Testing

| Component | Version | Used for |
|-----------|---------|----------|
| **pytest** | 9.1.1 | Test runner |
| **pytest-asyncio** | 1.4.0 | Async tests |
| **pytest-cov** | 7.1.0 | Coverage |
| **testcontainers** | 4.15.0 | Real Postgres+pgvector in integration tests |
| **hypothesis** | 6.164.0 | Property-based tests for rule engine invariants |
| **polyfactory** | 3.3.0 | Pydantic model factories |
| **Vitest** | 4.1.10 | Frontend unit tests |
| **Playwright** | 1.62.0 | E2E, primarily the review workflow |

**No mocked database in integration tests.** pgvector behaviour, transaction semantics and constraint
enforcement are exactly what we need to test; a mock would test our mock.

## Tooling

| Component | Version | Purpose |
|-----------|---------|---------|
| **ruff** | 0.16.0 | Lint + format (replaces black, isort, flake8) |
| **mypy** | 2.3.0 | Type checking, strict on L2 domain |
| **import-linter** | latest | **Enforces the layer contract in CI** |
| **pre-commit** | latest | Local gate |
| **Docker Compose** | 29.5.3 | Postgres, Redis, MinIO |

---

## Local runtime constraint

**The dev machine is an Apple M4 with 16 GB unified memory and ~42 GB free disk.** This is a real
architectural constraint, not a footnote.

Approximate steady-state budget with a 9 B model resident:

| Process | Memory |
|---------|--------|
| macOS + IDE + browser | ~4.5 GB |
| Ollama + Qwen3.5 9B Q4_K_M + 32K KV cache | ~10.5 GB |
| Postgres (Docker) | ~0.4 GB |
| Redis (Docker) | ~0.1 GB |
| FastAPI + Celery workers | ~0.6 GB |
| **Total** | **~16.1 GB** — at the limit |

Consequences that shape the design:

1. **Next.js dev server does not run at the same time as 9 B generation.** Compose profiles separate
   `backend`, `full` and `generate` so you start only what you need.
2. **Model concurrency is 1.** Enforced by the gateway's lease semaphore, not by convention.
3. **A fast tier exists.** Qwen3.5 4B (~3.5 GB) is the default for pipeline iteration; 9 B is used for
   content-quality work.
4. **Disk is budgeted at 15 GB for models.** Two or three quantised models, not a collection.

See [LLM Gateway & Local Models](07-llm-gateway-and-local-models.md) for the full model plan.
