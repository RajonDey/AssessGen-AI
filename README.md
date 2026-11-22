# AssessGen AI

Practice-test content generator for Reading, Writing, and Listening (script plus optional Kokoro TTS). A request is planned, generated, checked by structural rules, and reviewed.

Full design docs: [docs/README.md](docs/README.md). Paper shape (`topics`, `type_plan`, exports): [docs/modules/paper-spec.md](docs/modules/paper-spec.md).

---

## Install and run

You need **Python 3.12**, **Node.js 20+**, and [Ollama](https://ollama.com) when `LLM_PROVIDER=ollama`.

```bash
# once
curl -LsSf https://astral.sh/uv/install.sh | sh
ollama pull gemma4:12b          # or the model named in backend/.env

# project
make setup                      # Python deps, npm install, copy env files
# edit backend/.env             — LLM_PROVIDER, model names
# edit admin/.env.local         — NEXT_PUBLIC_API_URL (default http://127.0.0.1:8080)

make dev                        # API :8080 and admin :3001
```

- Generate UI: http://127.0.0.1:3001/generate
- API docs: http://127.0.0.1:8080/api/docs

Ollama must be running (`ollama serve` or the desktop app) when the provider is `ollama`. Do not run Kokoro TTS and a large local model at the same time on a 16 GB machine.

Listening WAV synthesis needs the TTS extra (`cd backend && uv sync --extra tts`). On Linux CPU, install PyTorch from the CPU index first — see [docs/installation.md](docs/installation.md).

Switch providers in `backend/.env`:

```bash
LLM_PROVIDER=ollama   # or openai
```

Example:

```bash
curl -s http://127.0.0.1:8080/api/v1/generate \
  -H 'Content-Type: application/json' \
  -d '{"module":"writing","topic":"remote work","target_band":6.5,"writing_type":"opinion"}'
```

Modules: `reading` | `writing` | `listening`.
