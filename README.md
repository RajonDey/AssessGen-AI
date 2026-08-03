# AssessGen AI

An **AI Assessment Content Engine** — a system that generates, validates, improves, versions and
exports assessment content. IELTS is the first target; the engine is deliberately not IELTS-only.

> **Status:** Phase 1A complete · Phase 1B complete (Reading) · **Phase 1C in progress** (Listening, Writing, Speaking).
> Track progress: [docs/execution/phase-1-checklist.md](docs/execution/phase-1-checklist.md).

---

## What this is

Not an IELTS question generator. An engine whose IELTS behaviour is one configurable pack, and whose
durable value lives in the workflow, the quality-control logic, the calibration data and the content
database — not in model weights.

**We do not train models. We build an engineered system around commodity LLMs.**

IELTS Ready is a *client* of this engine, consuming a public API. That separation is what makes the
engine sellable on its own terms later.

## The core idea

A generation request becomes a durable LangGraph workflow. Candidate content must then survive a
layered quality gate before it can be published:

```
L0 schema  →  L1 deterministic rules  →  L2 originality  →  L3 LLM critic  →  L4 human review
      cheap, certain  ─────────────────────────────────────▶  expensive, scarce
```

Deterministic rules produce **verdicts**; the LLM critic produces **findings, never a score**. Where
they disagree, the rule wins. Everything is versioned and immutable — nothing is ever overwritten.

## Documentation

Start at **[docs/README.md](docs/README.md)**.

| Read first | Why |
|---|---|
| [Product Strategy](docs/core/01-product-strategy.md) | What we are building and what "done" means |
| [System Architecture](docs/core/02-system-architecture.md) | The blueprint |
| [Quality & Evaluation](docs/core/08-quality-and-evaluation.md) | **The most important document** |
| [Execution Roadmap](docs/execution/roadmap.md) | Phased delivery plan |
| [Open Questions](docs/execution/open-questions.md) | What still needs deciding, and by when |

## Stack

**Backend** Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · Pydantic 2 · Celery + Redis
**AI** LangGraph 1.x · LangChain 1.x · Ollama (local-first, provider-agnostic gateway)
**Data** PostgreSQL 18 + pgvector 0.8.6 · S3/R2
**Frontend** Next.js 16 · React 19 · Tailwind 4 · TanStack Query
**Audio** Kokoro-82M (Apache 2.0)

All versions verified against live registries on 2026-07-30. See
[Tech Stack](docs/core/03-tech-stack.md) and [Dependencies](docs/core/10-dependencies.md).

## Development constraints worth knowing up front

- **Local-first.** Development uses local models via Ollama; no paid API calls. The production model
  decision is deliberately deferred until benchmark data exists.
- **16 GB unified memory.** Only one large model may be resident. Concurrency is bounded by a gateway
  lease, not by worker count.
- **LangChain/LangGraph are on v1 LTS.** Most online examples are 0.x and will mislead you. Official
  skills are installed in `.agents/skills/`.

## Repository layout

```
docs/                 Architecture, API, data model, quality system, roadmap
.cursor/rules/        AI agent rules (MDC) — layering, quality, copyright firewall
.agents/skills/       Installed LangChain/LangGraph official skills
backend/              (Phase 1) FastAPI app, agents, workers, domain
admin/                (Phase 1) Next.js admin dashboard
evals/                (Phase 1) Golden sets, benchmarks, calibration
infra/                Docker Compose, deployment
```

## Quick start

From a clean clone:

```bash
make setup          # uv sync, data stack, migrate, seed, pull Ollama model (host CLI)
make dev            # API + Celery worker (backend profile)
make test           # unit + integration
make lint           # ruff + mypy + import-linter
make verify-1a      # full Phase 1A exit check (includes smoke run against Ollama)
```

| Target | What it does |
|--------|----------------|
| `make setup` | Idempotent bootstrap via `scripts/setup.sh` |
| `make dev` | `docker compose --profile backend up -d` |
| `make generate` | `backend` profile + Ollama container for content runs |
| `make migrate` | `alembic upgrade head` |
| `make test-unit` | Domain and unit tests only (no testcontainers) |

Generation runs need Ollama with the `fast` profile model (`qwen3.5:4b`). Use `make generate` if you
do not run Ollama on the host.

## Local infrastructure (Docker Compose)

Copy environment defaults and start the data stack:

```bash
cp .env.example .env
docker compose --profile data up -d
./scripts/verify-data-services.sh
```

| Profile | Services | When to use |
|---------|----------|-------------|
| `data` | Postgres 18 + pgvector, Redis, MinIO | Migrations, integration tests |
| `backend` | `data` + API + Celery worker | Day-to-day backend dev |
| `generate` | `backend` + Ollama | Content generation runs |

Postgres runs on host port **5434** by default (avoids Homebrew Postgres on 5432 and other local projects on 5433). MinIO console:
http://localhost:9001

## A note on content integrity

This project handles authentic third-party exam material under a strict firewall: it informs
**structure and statistics only**, and its text is quarantined for use solely in negative
originality checks. It is never placed in a prompt and never used for training.

Read [Security, Copyright & Compliance](docs/core/11-security-copyright-compliance.md) before
touching anything under `evals/calibration/` or `reference_documents`.
