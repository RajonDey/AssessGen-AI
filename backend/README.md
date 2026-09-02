# AssessGen Backend — lightweight generation API

Full install guide: [docs/installation.md](../docs/installation.md)

## Requirements

| File | Install with |
| ---- | ------------ |
| `requirements.txt` | `uv sync` or `pip install -r requirements.txt` |
| `requirements-dev.txt` | `uv sync --extra dev` or `pip install -r requirements-dev.txt` |
| `requirements-tts.txt` | `uv sync --extra tts` or pip + CPU Torch index (see install doc) |

Regenerate from the lockfile after changing `pyproject.toml`:

```bash
uv export --no-dev --no-hashes -o requirements.txt
uv export --extra dev --no-hashes -o requirements-dev.txt
uv export --extra tts --no-hashes -o requirements-tts.txt
```

Python **3.12** only. Source of truth: `pyproject.toml` + `uv.lock`.

## Run without Docker

```bash
cd backend
cp .env.example .env   # if needed
uv sync --extra tts    # includes Kokoro; plain `uv sync` removes it
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
```

Docs: http://localhost:8080/api/docs

## Listening audio (Kokoro demo)

Optional TTS for uploaded Listening scripts (`speakers` + `script.turns`):

```bash
sudo apt-get install -y espeak-ng
cd backend
# Uses CPU Torch (see [tool.uv.sources] in pyproject.toml) — avoid CUDA on Intel demos
uv sync --extra tts
# unload Ollama models first if RAM is tight: ollama stop <model>
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
```

- Status: `GET /api/v1/listening/tts-status`
- Synthesize: `POST /api/v1/listening/synthesize` (multipart file)
- Admin UI: http://localhost:3001/listening-audio

## Provider switch

In `.env`:

```bash
LLM_PROVIDER=ollama   # or openai
OLLAMA_GENERATOR_MODEL=gemma4:e2b
OLLAMA_REVIEWER_MODEL=gemma4:e2b
# Optional larger model: ollama pull gemma4:12b

# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...
```

## Agents

1. **Generator** — creates reading / writing / listening (script) JSON  
2. **Reviewer** — validates; on failure generator revises (max 2 loops)
3. **TTS (optional)** — Kokoro turns Listening scripts into WAV (demo)
