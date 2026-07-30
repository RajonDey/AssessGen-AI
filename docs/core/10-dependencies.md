# 10 — Dependencies

All versions verified against live package registries on **2026-07-30**. Every dependency below has a
stated reason; anything without one should not be added.

## Policy

1. **Every dependency needs a justification.** Convenience is not one. Each addition is code we do not
   control running in our process.
2. **`uv.lock` and `pnpm-lock.yaml` are committed.** Reproducible installs are non-negotiable when
   provenance is a product feature.
3. **Semver-compliant packages** get `>=x.y,<x+1.0`. **Non-semver packages** (notably
   `langchain-community`) are pinned to an exact minor series.
4. **Prefer dedicated integration packages** over `langchain-community`. Community minor releases can
   break; dedicated packages are independently versioned.
5. **Security scanning weekly** (`pip-audit`, `pnpm audit`) via CI.
6. **A dependency that only saves a few lines does not get added.**

---

## Backend — runtime

### Web & config

```toml
fastapi          = ">=0.141,<0.142"   # async API + OpenAPI generation
uvicorn          = {extras=["standard"], version=">=0.38"}
pydantic         = ">=2.13,<3.0"      # also the L0 quality gate
pydantic-settings= ">=2.14,<3.0"      # typed env config
python-multipart = ">=0.0.20"         # file upload (reference corpus ingest)
```

### Database

```toml
sqlalchemy       = ">=2.0.51,<2.1"    # 2.0 typed style only
alembic          = ">=1.18,<2.0"      # migrations
psycopg          = {extras=["binary","pool"], version=">=3.3,<4.0"}
pgvector         = ">=0.5,<0.6"       # Python bindings for the vector type
```

`psycopg` v3, not psycopg2 — v3 has native async support, which the whole stack depends on.

### AI orchestration

```toml
langchain                    = ">=1.0,<2.0"
langchain-core               = ">=1.0,<2.0"   # peer dep — install explicitly
langgraph                    = ">=1.0,<2.0"
langgraph-checkpoint-postgres= ">=3.1,<4.0"   # durable paused runs
langchain-ollama             = ">=1.1,<2.0"   # local provider
langsmith                    = ">=0.10,<0.11" # tracing + eval datasets
```

> ⚠️ **v1 LTS.** Both LangChain and LangGraph are on the v1 line. The great majority of tutorials,
> Stack Overflow answers and model training data describe 0.x APIs and will actively mislead you.
> Consult the official skills in `.agents/skills/` before writing orchestration code.

**Not installed:** `langchain-community` — we have no need for it, and it does not follow semver.
Add only with a specific justification and an exact minor pin.

**Not installed:** `litellm` — see [Tech Stack](03-tech-stack.md) for why we write a thin gateway
instead.

### Queue & cache

```toml
celery = {extras=["redis"], version=">=5.6,<6.0"}
redis  = ">=8.1,<9.0"
flower = ">=2.0"                      # queue inspection UI; dev only
```

### NLP & quality tooling

These power the deterministic rule engine — the layer producing trustworthy signal.

```toml
textstat              = ">=0.7.13,<0.8"   # Flesch-Kincaid, Gunning Fog → readability
spacy                 = ">=3.8,<4.0"      # tokenisation, POS, sentence segmentation
wordfreq               = ">=3.1,<4.0"     # frequency bands → CEFR proxy
rapidfuzz             = ">=3.14,<4.0"     # fuzzy near-duplicate detection
datasketch            = ">=2.0,<3.0"      # MinHash/LSH for corpus overlap
sentence-transformers = ">=5.6,<6.0"      # optional local embeddings
```

Plus the spaCy model, installed separately (not a PyPI dependency):
`python -m spacy download en_core_web_sm`

`sentence-transformers` pulls in torch (~2 GB installed). It is **optional** — Ollama's
`nomic-embed-text` is the default embedding path and avoids that weight entirely. Keep it in an
`[embeddings-local]` extra rather than the base install.

### Audio (Listening — Phase 3)

```toml
kokoro     = ">=0.9.4,<1.0"    # Apache 2.0 TTS, commercially usable
soundfile  = ">=0.14,<0.15"
pydub      = ">=0.25"          # concatenation, silence gaps between speakers
```

System requirement: `espeak-ng` (`brew install espeak-ng`) — Kokoro's phonemiser.

### Storage & security

```toml
boto3            = ">=1.43,<2.0"       # S3 / Cloudflare R2
pyjwt            = ">=2.10,<3.0"       # JWT
argon2-cffi      = ">=25.1"            # password hashing
python-slugify   = ">=8.0"
```

**`argon2-cffi`, not `passlib` + bcrypt.** passlib 1.7.4 has been unmaintained for years and has known
friction with modern bcrypt releases. Argon2id is the current recommendation for password hashing.

**`pyjwt`, not `python-jose`.** python-jose has a history of slow security response and a larger
attack surface than we need for symmetric JWTs.

### Observability

```toml
structlog                        = ">=26.1,<27.0"
opentelemetry-api                = ">=1.44,<2.0"
opentelemetry-sdk                = ">=1.44,<2.0"
opentelemetry-instrumentation-fastapi     = "*"
opentelemetry-instrumentation-sqlalchemy  = "*"
prometheus-client                = ">=0.26,<1.0"
```

## Backend — development

```toml
pytest          = ">=9.1,<10.0"
pytest-asyncio  = ">=1.4,<2.0"
pytest-cov      = ">=7.1,<8.0"
testcontainers  = {extras=["postgres"], version=">=4.15,<5.0"}
hypothesis      = ">=6.164,<7.0"      # property-based tests for rule invariants
polyfactory     = ">=3.3,<4.0"        # Pydantic factories
ruff            = ">=0.16,<0.17"      # lint + format
mypy            = ">=2.3,<3.0"
import-linter   = ">=2.0"             # ENFORCES THE LAYER CONTRACT
pre-commit      = ">=4.0"
pip-audit       = ">=2.7"
```

`import-linter` is not optional tooling. It is the mechanism that keeps
[System Architecture](02-system-architecture.md) true over time.

---

## Frontend

```jsonc
{
  "dependencies": {
    "next": "16.2.12",
    "react": "19.2.8",
    "react-dom": "19.2.8",
    "@tanstack/react-query": "5.101.4",  // server state, optimistic review actions
    "zod": "4.4.3",                      // runtime validation of API responses
    "react-hook-form": "^7",
    "@hookform/resolvers": "^5",
    "lucide-react": "latest",
    "date-fns": "^4",
    "@dnd-kit/core": "^6"                // drag-and-drop test builder
  },
  "devDependencies": {
    "typescript": "~5.9",                // NOT 7.0 yet — see note
    "tailwindcss": "4.3.3",
    "@tailwindcss/postcss": "4.3.3",
    "vitest": "4.1.10",
    "@playwright/test": "1.62.0",
    "eslint": "^9",
    "openapi-typescript": "^7",          // generates the API client
    "@types/react": "^19",
    "@types/node": "^24"
  }
}
```

**TypeScript 5.9, not 7.0.** TypeScript 7.0 is available but is a major release; the surrounding
ecosystem (ESLint plugins, Next.js internals, type packages) needs verification before adoption. This
is a deliberate, revisitable lag — not an oversight. Re-evaluate at the start of Phase 2.

**shadcn/ui** is not a dependency — components are generated into `src/components/ui/` and owned by
us. That is the point: accessible primitives with no version lock-in.

---

## Infrastructure

```yaml
postgres: pgvector/pgvector:pg18       # Postgres 18 + pgvector 0.8.6
redis:    redis:8-alpine
minio:    minio/minio:latest           # local S3-compatible storage for dev
```

Local Homebrew Postgres 14.18 must **not** be used. Version, extensions and locale differences between
dev and production are a classic source of bugs that appear only in production.

---

## System prerequisites (macOS)

```bash
# Present and verified on this machine
uv 0.11.8 · node 24.2.0 · pnpm 11.0.9 · docker 29.5.3 · ollama 0.31.1 · git 2.49.0

# Needed
brew install espeak-ng      # Kokoro phonemiser (Phase 3)
uv python install 3.12      # project Python — NOT the system 3.14.6
```

### Ollama models

```bash
ollama pull qwen3.5:9b        # 6.6 GB  generator (local profile)
ollama pull qwen3.5:4b        # 3.5 GB  metadata + fast profile
ollama pull nomic-embed-text  # 0.3 GB  embeddings (768 dims)
# llama3.2:1b already present — test suites only
# Total ≈ 10.4 GB of the 15 GB model disk budget (42 GB free)
```

---

## Dependency risk register

| Dependency | Risk | Mitigation |
|-----------|------|------------|
| **LangGraph/LangChain v1** | Fast-moving; API churn between minors | Pinned `<2.0`; official skills installed; orchestration isolated in `workflows/` |
| **Ollama** | Not an official LangChain-maintained runtime; version drift | Provider isolated behind the gateway; swappable |
| **Kokoro** | Small project, single maintainer | Apache 2.0 — we can vendor it. Only used in Phase 3 |
| **spaCy + torch** | Large install; wheel lag on new Python majors | Python pinned to 3.12; torch path is optional |
| **pgvector** | Dimension change requires migration + re-embed | Model name stored per row so mixed state is detectable |
| **Next.js 16** | Frequent majors | Admin is internal; upgrades can be deferred safely |
| **TypeScript 7** | Ecosystem readiness unknown | Staying on 5.9; revisit Phase 2 |

---

## Bootstrap sequence

Not to be executed yet — this is the Phase 1 setup contract.

```bash
# 1. Python toolchain
uv python install 3.12
uv venv --python 3.12
uv sync

# 2. Services
docker compose --profile data up -d      # postgres + redis + minio
uv run alembic upgrade head
uv run python -m app.scripts.seed        # org, admin user, topics, rule catalogue

# 3. Models
ollama pull qwen3.5:9b && ollama pull qwen3.5:4b && ollama pull nomic-embed-text

# 4. NLP data
uv run python -m spacy download en_core_web_sm

# 5. Frontend
cd admin && pnpm install && pnpm gen:client

# 6. Verify
make lint && make test-unit
```

All of this is wrapped by `make setup`.
