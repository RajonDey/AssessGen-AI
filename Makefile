# AssessGen AI — lightweight commands (repo root)
.PHONY: setup sync dev docker-up docker-down admin-dev be-dev eval requirements

BACKEND := backend
COMPOSE := docker compose

setup: sync
	@test -f backend/.env || cp backend/.env.example backend/.env
	@test -f .env || cp .env.example .env
	@test -f admin/.env.local || cp admin/.env.example admin/.env.local
	cd admin && npm install
	@echo "Setup done. Run: make dev"

sync:
	cd $(BACKEND) && uv sync

# Regenerate pip-compatible requirements from uv.lock (after pyproject.toml changes)
requirements:
	cd $(BACKEND) && uv export --no-dev --no-hashes -o requirements.txt
	cd $(BACKEND) && uv export --extra dev --no-hashes -o requirements-dev.txt
	cd $(BACKEND) && uv export --extra tts --no-hashes -o requirements-tts.txt
	@echo "Updated backend/requirements*.txt"

dev:
	chmod +x scripts/dev-local.sh
	./scripts/dev-local.sh

be-dev:
	cd $(BACKEND) && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000

admin-dev:
	cd admin && npm run dev

# Phase 3 — structural eval harness (samples + planted defects)
eval:
	cd $(BACKEND) && uv run python evals_runner.py

docker-up:
	$(COMPOSE) up -d --build api

docker-down:
	$(COMPOSE) down
