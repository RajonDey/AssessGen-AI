# IELTS module persistence (Phase 1C convention)

Thin verticals reuse **`passages` / `passage_versions`** and **`items` / `item_versions`**. Module-specific
shape lives in JSON bodies and run `request.spec` — no new tables in Phase 1C.

| Module | Primary artefact | Storage |
|--------|------------------|---------|
| Reading | Passage + items | `passage_versions.body` (labelled text); items as today |
| Listening | Script + items | `passage_versions.body` = transcript text; `metadata` = script JSON (speakers, turns) |
| Writing | Task 2 prompt | `passage_versions.body` = prompt text; `metadata` = `{task, question_type}` |
| Speaking | Part 1 + Part 2 | `passage_versions.body` = structured JSON (topics + cue card) |

Human review and bank APIs stay module-agnostic; admin UI renders by `generation_runs.module`.

See [Phase 1C execution plan](../../../docs/execution/phase-1c-thin-verticals.md).
