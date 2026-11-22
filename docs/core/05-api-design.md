# 05 — API Design

## Principles

1. **Resource-shaped, not verb-shaped.** The original sketch had `POST /generate-reading`,
   `POST /evaluate`, `POST /publish`. Those read well but do not compose, version or cache. We model
   the *things* — runs, items, reviews, publications — and act on them.
2. **Generation is asynchronous.** A run takes minutes. No HTTP request waits for one. Every
   generation returns `202` with a run resource to poll or stream.
3. **Two audiences, two surfaces.** The **Admin API** is rich, authenticated per user, and shaped for
   the dashboard. The **Consumer API** is narrow, read-only, key-authenticated and immutable — it is
   what IELTS Ready and future licensees use. They version independently.
4. **Immutable reads are aggressively cacheable.** A published test never changes, so it carries a
   strong `ETag` and a long `Cache-Control`.
5. **The OpenAPI schema is the contract.** The TypeScript client is generated from it. Hand-written
   API types drift and then lie.

Base paths: `/api/v1/...` (admin) and `/api/consumer/v1/...` (external).

---

## Conventions

| Concern | Rule |
|---------|------|
| IDs | UUIDv7 (time-sortable) as strings |
| Timestamps | RFC 3339 UTC, `_at` suffix |
| Casing | `snake_case` throughout |
| Pagination | Cursor-based: `?limit=50&cursor=...` → `{data, next_cursor}` |
| Filtering | Explicit query params only. No generic query language |
| Errors | RFC 9457 Problem Details |
| Idempotency | `Idempotency-Key` header **required** on every generation POST |
| Correlation | `X-Request-Id` echoed and attached to every log and span |
| Versioning | Breaking changes → new path prefix. Additive changes → same version |

### Error shape

```json
{
  "type": "https://assessgen.ai/errors/quality-gate-blocked",
  "title": "Item blocked by quality gate",
  "status": 409,
  "detail": "Item cannot be approved while MUST-level rules are failing.",
  "instance": "/api/v1/items/018f.../versions/018f.../review",
  "request_id": "req_01J2X...",
  "violations": [
    { "rule_code": "R-READ-001", "severity": "must",
      "message": "Answer 'photosynthesis process' is not a verbatim substring of the passage." }
  ]
}
```

Errors that a human must act on always carry machine-readable `violations`. The dashboard renders
them directly, so a reviewer sees exactly what is wrong rather than "validation failed".

---

## Running API (current code)

The lightweight server exposes generation on `POST /api/v1/generate` (and `POST /api/v1/generate/stream`). `module` is still a body field (`reading` | `writing` | `listening`). The request is `GenerateRequest` in `backend/app/schemas/generation.py`.

| Field | Role |
|-------|------|
| `topic` | Primary / display topic (usually Part 1 or Task 1) |
| `topics` | Independent topic per part. Listening: 4, Reading: 3. Writing may use `topics[2]` or `topic_t1` / `topic_t2` |
| `type_plan` | Per-part item-type lists. Omitted plans are filled from `app.content.paper_spec` |
| `task1_kind` / `task2_kind` | Writing only. `task2_kind` tracks `writing_type` |
| `target_band` | Target difficulty |

Invalid specs fail with `SPEC-*` codes. Defaults, interlocking rules, and admin PDF / MD / TTS JSON downloads are in [Paper spec](../modules/paper-spec.md).

Also live today:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/generate/cost-stats` | In-process LLM call counts (`app.content.cost_ledger`) |
| `POST` | `/api/v1/generate/cost-stats/reset` | Clear that ledger |
| `POST` | `/api/v1/listening/synthesize` | Kokoro WAV from a TTS-ready Listening script (optional extra) |

The routes below are the target admin contract. They are not all implemented in this tree.

---

## Admin API

### Generation

```http
POST /api/v1/generation/runs
Idempotency-Key: 4f9c2a10-...
```

One endpoint for all modules — `module` is a field, not a path segment. This is what lets a new exam
format ship without touching routing.

```json
{
  "module": "reading",
  "exam": "ielts",
  "variant": "academic",
  "spec": {
    "target_band": 7.0,
    "topic": "environment",
    "passage_count": 3,
    "question_count": 40,
    "difficulty_curve": ["easy", "medium", "hard"],
    "question_types": ["mcq_single", "true_false_notgiven", "heading_match", "sentence_completion"]
  },
  "options": { "auto_revise": true, "max_revision_loops": 2, "require_human_review": true }
}
```

```http
202 Accepted
Location: /api/v1/generation/runs/018f3a...
```
```json
{ "run_id": "018f3a...", "status": "queued", "module": "reading",
  "created_at": "2026-07-30T12:00:00Z" }
```

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/generation/runs` | List runs; filter by `status`, `module`, `created_after` |
| `GET /api/v1/generation/runs/{id}` | Full run state, plan, progress, cost, produced item IDs |
| `GET /api/v1/generation/runs/{id}/events` | **SSE** live progress stream |
| `GET /api/v1/generation/runs/{id}/invocations` | Per-call ledger: model, tokens, latency, prompt hash |
| `POST /api/v1/generation/runs/{id}/cancel` | Cooperative cancel at the next checkpoint |
| `POST /api/v1/generation/runs/{id}/resume` | Resume a run paused at a human interrupt |
| `POST /api/v1/generation/runs/{id}/replay` | Re-run with identical prompt/model/seed — reproducibility check |
| `POST /api/v1/generation/batches` | Bulk fan-out: N runs from a matrix spec |

**SSE rather than websockets.** Progress is one-directional server→client. SSE reconnects natively,
traverses proxies cleanly, and needs no extra infrastructure.

`POST .../resume` maps onto LangGraph's `Command(resume=...)` against the run's `thread_id`:

```json
{ "decision": "approve", "notes": "Passage 2 heading set reworded." }
```

### Question bank

```http
GET /api/v1/items?module=reading&item_type=true_false_notgiven
                 &band_min=6.5&band_max=7.5&topic=environment
                 &status=approved&has_audio=false&limit=50&cursor=...
```

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/items` | Filtered bank listing (returns current version inline) |
| `GET /api/v1/items/{id}` | Item with current version and quality summary |
| `GET /api/v1/items/{id}/versions` | Full version history |
| `GET /api/v1/items/{id}/versions/{vid}` | A specific immutable version |
| `POST /api/v1/items/{id}/versions` | **Manual edit** → creates a new version, re-runs the gate |
| `POST /api/v1/items/{id}/revise` | **AI revision** → queues a reviser run against findings |
| `POST /api/v1/items/{id}/archive` | Withdraw from use (retained) |
| `GET /api/v1/items/{id}/similar` | pgvector nearest neighbours — duplicate inspection |
| `GET /api/v1/passages/...` | Same shape for passages |

There is no `PATCH /items/{id}` and no `DELETE`. Editing creates a version; removal is archival. The
API surface makes the immutability guarantee structural rather than advisory.

### Quality

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/quality/evaluate` | Run the gate on an existing version (sync for rules, async if the critic is included) |
| `GET /api/v1/quality/checks?target_id=...` | All checks for a version |
| `GET /api/v1/quality/rules` | Rule catalogue: code, severity, description, engine version |
| `GET /api/v1/quality/reports/summary` | Pass rates by rule, module, band, time window |
| `GET /api/v1/quality/reports/coverage` | Topic × band × type matrix, with gaps |
| `GET /api/v1/quality/reports/calibration` | **Rule engine vs authentic material** — false-positive rate |

The calibration report is the one that tells us whether our rules are trustworthy. It is a
first-class endpoint, not a script.

### Review

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/review/queue` | Prioritised queue; `?assigned_to=me&module=reading` |
| `GET /api/v1/review/queue/next` | Atomically claim the next item (prevents two reviewers colliding) |
| `POST /api/v1/items/{id}/versions/{vid}/review` | Record a decision |
| `GET /api/v1/review/stats` | Throughput, approval rate, minutes per item, by reviewer |

```json
POST /api/v1/items/{id}/versions/{vid}/review
{ "decision": "request_changes",
  "reason_code": "weak_distractor",
  "comment": "Options B and C are both defensible under paragraph D.",
  "time_spent_seconds": 95 }
```

`reason_code` comes from a fixed vocabulary served by `GET /api/v1/review/reason-codes`. Free-text
comments are for humans; reason codes are what we aggregate to improve prompts.

Returns `409` with `violations` if the target is `blocked` — a human cannot approve past a MUST rule.

### Test builder & publishing

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/question-sets` | Create a set from item **version** IDs |
| `POST /api/v1/question-sets/auto` | Auto-assemble from a spec, drawing on approved items |
| `POST /api/v1/mock-tests` | Compose sections into a test |
| `POST /api/v1/mock-tests/{id}/validate` | Structural check before publishing |
| `POST /api/v1/mock-tests/{id}/publish` | **Freeze** into an immutable publication |
| `POST /api/v1/publications/{id}/revoke` | Withdraw (never delete) |
| `POST /api/v1/exports` | Async export job → PDF / DOCX / JSON |

### Prompts, models, admin

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/prompts` · `GET /api/v1/prompts/{name}/versions` | Prompt registry (mirrors git) |
| `POST /api/v1/prompts/{name}/versions/{v}/activate` | Activate / rollback |
| `POST /api/v1/prompts/{name}/versions/{v}/evaluate` | Run against the golden set — **required before activation** |
| `GET /api/v1/models` | Configured roles, models, health, memory footprint |
| `GET /api/v1/models/benchmarks` | Benchmark harness results by model — the server-purchase evidence |
| `GET /api/v1/analytics/costs` | Cost/latency by run, model, module, period |

### Auth

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/auth/login` | Email + password → short-lived JWT + refresh cookie |
| `POST /api/v1/auth/refresh` · `POST /api/v1/auth/logout` | Session management |
| `GET /api/v1/auth/me` | Current user + permissions |

---

## Consumer API

Deliberately tiny, read-only, and immutable. This is the boundary between the engine and IELTS Ready,
and later the surface we would sell.

```http
GET /api/consumer/v1/publications?exam=ielts&variant=academic&module=reading
GET /api/consumer/v1/publications/{id}          → the frozen snapshot
GET /api/consumer/v1/publications/{id}/manifest → hashes + asset URLs, cheap sync check
GET /api/consumer/v1/assets/{id}                → 302 to a signed, expiring URL
```

- Auth: `Authorization: Bearer <api_key>`, scoped per organization.
- `GET /publications/{id}` returns `ETag` and `Cache-Control: public, max-age=31536000, immutable` —
  it is safe because the snapshot genuinely never changes.
- Answer keys are **omitted by default** and require the `content:answers` scope, so a client-side
  consumer cannot leak them.
- Revoked publications return `410 Gone` with a pointer to the superseding publication.

**Why this separation earns its keep.** IELTS Ready cannot reach draft content, cannot mutate
anything, and cannot be broken by an admin refactor. That constraint is what makes the "engine as a
product" strategy real rather than aspirational — the day a third party wants access, we hand them a
key rather than build a new system.

---

## Cross-cutting behaviour

**Idempotency.** Generation POSTs require `Idempotency-Key`. Replaying a key within 24 h returns the
original run rather than starting a second expensive one. Enforced by a unique constraint on
`(organization_id, idempotency_key)`, so a race loses at the database rather than in application code.

**Rate limiting.** Per-user and per-key token buckets in Redis. Generation endpoints are limited by
*concurrent runs*, not requests per second — the real scarce resource is the model, not HTTP.

**Long-running work.** Anything over ~2 s is a job: `202` + resource + poll or SSE. This includes
exports, batch generation, re-embedding and bulk revision.

**Permissions.**

| Role | Capabilities |
|------|--------------|
| `viewer` | Read bank, read reports |
| `reviewer` | + review decisions, manual edits |
| `operator` | + start generation, assemble tests |
| `admin` | + publish, prompts, models, users |

Publishing is deliberately admin-only. It is the one irreversible-in-practice action in the system.
