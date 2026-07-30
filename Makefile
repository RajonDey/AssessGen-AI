# AssessGen AI — common tasks (run from repo root)
.PHONY: setup dev generate test test-unit lint migrate seed verify-1a

BACKEND := backend
COMPOSE := docker compose

setup:
	./scripts/setup.sh

dev:
	$(COMPOSE) --profile backend up -d

generate:
	$(COMPOSE) --profile generate up -d

test:
	cd $(BACKEND) && uv run pytest tests/unit tests/integration -q

test-unit:
	cd $(BACKEND) && uv run pytest tests/unit -q

lint:
	cd $(BACKEND) && uv run ruff check app tests
	cd $(BACKEND) && uv run ruff format --check app tests
	cd $(BACKEND) && uv run mypy app tests
	cd $(BACKEND) && uv run lint-imports

migrate:
	cd $(BACKEND) && uv run alembic upgrade head

seed:
	cd $(BACKEND) && uv run python -m app.scripts.seed

verify-1a:
	./scripts/verify-1a.sh
