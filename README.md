# AssessGen AI

Lightweight **IELTS practice content generator**: Reading, Writing, and Listening
(scripts + optional Kokoro TTS). Two agents: **generator** → **rules + reviewer**.

Skills live in `backend/app/skills/`. Structural rules in `backend/app/rules/`.

**Install:** [docs/installation.md](docs/installation.md) (requirements, Ollama, TTS, env files)

Switch providers in `backend/.env`:

```bash
LLM_PROVIDER=ollama   # or openai
```

---

## Run without Docker (recommended)

```bash
# once
curl -LsSf https://astral.sh/uv/install.sh | sh   # if needed
make setup

# daily — API :8080 + admin :3001
make dev
```

- UI: http://localhost:3001/generate  
- API docs: http://localhost:8080/api/docs  
- Ollama must be running on the host if `LLM_PROVIDER=ollama`  
- The admin UI talks to the API at `http://127.0.0.1:8080` directly (avoids Next.js proxy timeouts on long generations)

Or separately:

```bash
make be-dev      # terminal 1 (port 8000 — see Makefile)
make admin-dev   # terminal 2
```

**Python deps:** `backend/requirements.txt` (runtime), `requirements-dev.txt`, `requirements-tts.txt` — see [installation](docs/installation.md).

---

## Run API with Docker (optional)

```bash
make docker-up
# Admin still local:
make admin-dev
```

Ollama on the host is reached via `host.docker.internal`.  
Optional Compose Ollama: `docker compose --profile ollama up -d`

---

## API

```bash
curl -s http://localhost:8080/api/v1/generate \
  -H 'Content-Type: application/json' \
  -d '{"module":"writing","topic":"remote work","target_band":6.5,"writing_type":"opinion"}'
```

Modules: `reading` | `writing` | `listening`

---

## What was removed

Postgres, Redis, MinIO, Celery, LangGraph, quality corpus, auth/review bank — not needed for
simple generation. Listening **audio** is deferred.
