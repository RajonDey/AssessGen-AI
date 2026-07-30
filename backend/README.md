# AssessGen Backend

FastAPI application, LangGraph workflows, Celery workers, and domain logic.

See [docs/core/06-folder-structure.md](../docs/core/06-folder-structure.md) for layout and
[docs/execution/phase-1a-foundation.md](../docs/execution/phase-1a-foundation.md) for the current
build plan.

## Quick start

```bash
uv sync --extra dev
uv run python -c "import app"
uv run pytest tests/unit -q
```

## Lint (T2)

```bash
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy app tests
uv run lint-imports
```

Pre-commit (from repo root):

```bash
cd backend && uv sync --extra dev
cd .. && uv run --directory backend pre-commit install
pre-commit run --all-files
```

## Database

Requires Docker data profile (`docker compose --profile data up -d`). Postgres on host port **5433**.

```bash
uv run alembic upgrade head
uv run python -m app.scripts.seed
```

Default seed admin: `admin@assessgen.local` / `admin` (override with `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD`).

## Celery worker

Requires Redis (`docker compose --profile data up -d`). **Run from `backend/`** — the uv project lives here, not at the repo root.

```bash
cd backend
uv sync --extra dev
uv run celery -A app.infrastructure.queue.celery_app worker \
  --loglevel=info -Q q.generate,q.io,q.audio --concurrency=1
```

## Smoke generation run (T9)

With API, worker, Redis, Postgres, and Ollama running:

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@assessgen.local","password":"admin"}' | jq -r .access_token)

# Queue smoke run
curl -s -X POST http://localhost:8000/api/v1/generation/runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: $(uuidgen)" \
  -H 'Content-Type: application/json' \
  -d '{"module":"smoke","spec":{"kind":"smoke"}}'

# Poll status
curl -s http://localhost:8000/api/v1/generation/runs/<run_id> \
  -H "Authorization: Bearer $TOKEN"
```
