# Installation

Local setup for the lightweight AssessGen stack: **FastAPI backend**, **Next.js admin UI**, and **Ollama** (or an OpenAI-compatible API) for generation.

---

## Requirements

### System

| Component | Version | Notes |
| --------- | ------- | ----- |
| **Python** | 3.12.x | 3.13+ is not supported yet (`requires-python` in `backend/pyproject.toml`) |
| **Node.js** | 20+ | Admin UI (Next.js 16) |
| **npm** | 10+ | Ships with Node |
| **Ollama** | latest | Required when `LLM_PROVIDER=ollama` |
| **uv** | latest | Recommended Python installer (or use pip + `requirements.txt`) |
| **espeak-ng** | optional | Linux TTS only — Kokoro phonemizer dependency |

### Hardware (local LLM)

- **16 GB RAM** minimum for one large Ollama model at a time (e.g. `gemma4:12b` on CPU).
- Do not run Kokoro TTS and a large Ollama model together on the same machine.
- Intel/AMD CPU inference is supported; GPU is optional.

### Python packages

Declared in `backend/pyproject.toml`. Locked exports:

| File | Purpose |
| ---- | ------- |
| [`backend/requirements.txt`](../backend/requirements.txt) | Runtime API (generation + rules) |
| [`backend/requirements-dev.txt`](../backend/requirements-dev.txt) | Runtime + pytest + ruff |
| [`backend/requirements-tts.txt`](../backend/requirements-tts.txt) | Runtime + Kokoro TTS (Listening WAV demo) |

Regenerate after dependency changes:

```bash
cd backend
uv export --no-dev --no-hashes -o requirements.txt
uv export --extra dev --no-hashes -o requirements-dev.txt
uv export --extra tts --no-hashes -o requirements-tts.txt
```

### Node packages

See [`admin/package.json`](../admin/package.json). Installed via `npm install` in `admin/`.

---

## Quick start (recommended)

From the repo root:

```bash
# 1. Install uv (once)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install Ollama (once) — https://ollama.com
#    Then pull a model that matches backend/.env, e.g.:
ollama pull gemma4:12b

# 3. One-time project setup
make setup

# 4. Edit LLM settings
#    backend/.env  — OLLAMA_GENERATOR_MODEL, OLLAMA_REVIEWER_MODEL
#    admin/.env.local — NEXT_PUBLIC_API_URL (default http://127.0.0.1:8080)

# 5. Run API + admin UI
make dev
```

Open:

- **Generate UI:** http://127.0.0.1:3001/generate  
- **API docs:** http://127.0.0.1:8080/api/docs  

Ensure Ollama is running (`ollama serve` or the desktop app) when `LLM_PROVIDER=ollama`.

---

## Manual setup

### 1. Backend — uv (preferred)

```bash
cd backend
cp .env.example .env          # configure LLM provider + models
uv sync                       # core API only
uv sync --extra dev           # + pytest, ruff
uv sync --extra tts           # + Kokoro (Listening audio)
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
```

**Important:** Plain `uv sync` drops optional extras. Use `--extra tts` whenever you need Listening WAV synthesis.

### 2. Backend — pip

From `backend/` with Python 3.12:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip

# Core API
pip install -r requirements.txt

# Or with dev / TTS extras
pip install -r requirements-dev.txt
pip install -r requirements-tts.txt   # see TTS note below for CPU Torch on Linux
```

For **TTS on Linux (CPU Torch)**, install PyTorch from the CPU index before `requirements-tts.txt`:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-tts.txt
```

(`pyproject.toml` configures the same CPU index for `uv sync --extra tts`.)

### 3. Admin UI

```bash
cd admin
cp .env.example .env.local
npm install
npm run dev    # http://127.0.0.1:3001
```

The UI calls the API directly at `NEXT_PUBLIC_API_URL` to avoid Next.js proxy timeouts on long local generations.

### 4. Ollama models

Set model names in `backend/.env` to match `ollama list`:

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_GENERATOR_MODEL=gemma4:12b
OLLAMA_REVIEWER_MODEL=gemma4:12b
```

Suggested local models for Listening (long JSON scripts):

| Model | Role | Notes |
| ----- | ---- | ----- |
| `gemma4:12b` | Generator + reviewer | Best local quality; slow on CPU; use `think: false` for long papers (handled in client) |
| `qwen2.5:7b` | Fast experiments | Often short stubs; good for pipeline debugging only |
| `gemma4:e2b` | Not recommended | Frequently returns blank output |

Pull before first run:

```bash
ollama pull gemma4:12b
```

### 5. Listening TTS (optional)

System dependency on Linux:

```bash
sudo apt-get install -y espeak-ng
```

Then:

```bash
cd backend
uv sync --extra tts
ollama stop <model>    # free RAM before Kokoro loads
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
```

- TTS status: `GET /api/v1/listening/tts-status`  
- Synthesize: `POST /api/v1/listening/synthesize` (upload JSON)  
- Admin: http://127.0.0.1:3001/listening-audio  

---

## Environment files

| File | Purpose |
| ---- | ------- |
| `backend/.env` | LLM provider, model names, revision loops, timeouts |
| `admin/.env.local` | `NEXT_PUBLIC_API_URL` for the browser |
| `.env` (repo root) | Docker Compose overrides only |

Copy from `.env.example` / `backend/.env.example` / `admin/.env.example` if missing (`make setup` does this).

### OpenAI-compatible provider

In `backend/.env`:

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_GENERATOR_MODEL=gpt-4o-mini
OPENAI_REVIEWER_MODEL=gpt-4o-mini
```

Restart the API after changes (`get_settings()` is cached at startup).

---

## Verify installation

```bash
# Backend tests
cd backend && uv run pytest -q

# API health
curl -s http://127.0.0.1:8080/api/docs | head -5

# Generate (requires Ollama or OpenAI configured)
curl -s http://127.0.0.1:8080/api/v1/generate \
  -H 'Content-Type: application/json' \
  -d '{"module":"writing","topic":"remote work","target_band":6.5,"writing_type":"opinion"}'
```

---

## Docker (optional)

API only — admin still runs locally:

```bash
make docker-up
make admin-dev
```

Ollama on the host is reached via `host.docker.internal` (see root `.env.example`).

---

## Troubleshooting

| Symptom | Fix |
| ------- | --- |
| `Ollama model … not installed` | `ollama pull <model>`; match name in `backend/.env` |
| `document.empty_raw` / blank generation | Gemma 4 thinking bug — restart API after client updates; use `think: false` for papers |
| `generation.unusable_output` for Listening | Model returned Markdown, not JSON with `script.turns` — retry or use a stronger model |
| Listening audio 503 | Run `uv sync --extra tts`; install `espeak-ng` on Linux |
| Admin cannot reach API | Check `admin/.env.local` → `NEXT_PUBLIC_API_URL=http://127.0.0.1:8080` |
| Out of memory | `ollama stop <model>`; run only one large model; do not run TTS + Ollama together |

---

## Related docs

- [Backend README](../backend/README.md) — API-focused quick reference  
- [Dependencies (full stack plan)](core/10-dependencies.md) — long-term pinned deps for the full engine  
- [LLM Gateway & local models](core/07-llm-gateway-and-local-models.md) — memory budget and model roles  
