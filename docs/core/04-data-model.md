# 04 — Data Model

## The two ideas that drive the whole schema

### 1. Content is immutable; identity is stable

An "item" is a stable identity. Its *content* lives in immutable versions. Editing never mutates a
row — it appends a version and moves a pointer.

```
items (identity, stable UUID)  ──current_version_id──▶  item_versions (immutable, append-only)
```

This is not bookkeeping pedantry. It is what makes these things possible:

- A student who sat a test in 2026 can have their paper reproduced exactly in 2030.
- A prompt regression can be detected by diffing v3 against v2 of the same item.
- A defect found in production can be traced to the exact model + prompt that produced it.
- Rollback is moving a pointer, not restoring a backup.

`UPDATE` on a `*_versions` table is a bug. This is enforced by a database trigger, not by discipline.

### 2. Provenance is a first-class citizen

Every version records **which run made it, from which prompt version, on which model, with which
sampling parameters.** Without this, quality work is guesswork: you cannot tell whether last week's
improvement came from the new prompt, the new model or luck.

---

## Entity map

```
organizations
  └── users ── reviews
  └── generation_runs ──── agent_invocations
         │                        │
         │ produces               │ traced by
         ▼                        ▼
     passages ──▶ passage_versions ◀── quality_checks
         │              │
         │              └── embeddings
         ▼
       items ────▶ item_versions ◀────── quality_checks
                        │      │
                        │      └── embeddings
                        │
              question_set_items
                        │
                  question_sets ──▶ mock_tests ──▶ publications (frozen snapshot)

  prompt_versions          (git is source of truth; DB mirrors for FK integrity)
  reference_documents      (QUARANTINED corpus — negative checks only)
  topics / tags
```

---

## Tenancy

You said the engine is internal for now, with possible API/question-pack sales later. The schema
therefore carries `organization_id` on every content table from the first migration, with a single
seeded row (`internal`).

**Why do this now when there is one tenant?** The column costs nothing today. Adding it later means
backfilling every table, auditing every query for missing scope, and retrofitting authorization —
across a database that by then holds real content. This is a rare case where the cheap hedge is
genuinely near-free and the deferred cost is large and non-linear.

What we are **not** building now: org management UI, roles beyond a simple enum, billing, per-tenant
config, row-level security policies. Those are Phase 4 and are not implied by the column.

---

## Tables

### Identity & tenancy

```sql
organizations (
  id              uuid PRIMARY KEY,
  slug            text UNIQUE NOT NULL,
  name            text NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now()
)

users (
  id              uuid PRIMARY KEY,
  organization_id uuid NOT NULL REFERENCES organizations(id),
  email           citext UNIQUE NOT NULL,
  password_hash   text NOT NULL,
  role            text NOT NULL,     -- 'admin' | 'operator' | 'reviewer' | 'viewer'
  is_active       boolean NOT NULL DEFAULT true,
  created_at      timestamptz NOT NULL DEFAULT now()
)
```

### Provenance

```sql
generation_runs (
  id                 uuid PRIMARY KEY,          -- also the LangGraph thread_id
  organization_id    uuid NOT NULL REFERENCES organizations(id),
  module             text NOT NULL,             -- 'reading'|'listening'|'writing'|'speaking'
  request            jsonb NOT NULL,            -- the validated API request, verbatim
  plan               jsonb,                     -- Planner output
  status             text NOT NULL,             -- see run lifecycle below
  failure_reason     text,
  idempotency_key    text,
  requested_by       uuid REFERENCES users(id),
  started_at         timestamptz,
  finished_at        timestamptz,
  total_input_tokens   bigint NOT NULL DEFAULT 0,
  total_output_tokens  bigint NOT NULL DEFAULT 0,
  total_latency_ms     bigint NOT NULL DEFAULT 0,
  estimated_cost_usd   numeric(12,6) NOT NULL DEFAULT 0,
  created_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, idempotency_key)
)

-- One row per LLM call. This is the cost/latency ledger and the reproducibility record.
agent_invocations (
  id                 uuid PRIMARY KEY,
  run_id             uuid NOT NULL REFERENCES generation_runs(id) ON DELETE CASCADE,
  agent              text NOT NULL,             -- 'planner'|'passage'|'question'|'answer'|'critic'|'reviser'
  role               text NOT NULL,             -- gateway role: 'generator'|'critic'|'metadata'|'embedding'
  provider           text NOT NULL,             -- 'ollama'|'openai'|'anthropic'|...
  model_name         text NOT NULL,
  model_digest       text,                      -- exact weights identifier
  prompt_version_id  uuid REFERENCES prompt_versions(id),
  prompt_hash        text NOT NULL,             -- sha256 of the fully rendered prompt
  params             jsonb NOT NULL,            -- {temperature, top_p, seed, max_tokens, ...}
  input_tokens       int, output_tokens int,
  latency_ms         int, tokens_per_second numeric(10,2),
  cost_usd           numeric(12,6) NOT NULL DEFAULT 0,   -- 0 for local
  status             text NOT NULL,             -- 'ok'|'schema_error'|'timeout'|'provider_error'
  error_detail       text,
  attempt            int NOT NULL DEFAULT 1,
  created_at         timestamptz NOT NULL DEFAULT now()
)
```

`prompt_hash` + `model_digest` + `params.seed` is the reproducibility triple. With all three, a run
can be replayed. Without any one of them, it cannot.

### Content — passages

```sql
passages (
  id                 uuid PRIMARY KEY,
  organization_id    uuid NOT NULL REFERENCES organizations(id),
  module             text NOT NULL,             -- 'reading' | 'listening'
  current_version_id uuid,                      -- FK added after passage_versions exists
  status             text NOT NULL,             -- lifecycle, see below
  created_at         timestamptz NOT NULL DEFAULT now()
)

passage_versions (
  id                 uuid PRIMARY KEY,
  passage_id         uuid NOT NULL REFERENCES passages(id) ON DELETE CASCADE,
  version_no         int NOT NULL,
  content_hash       text NOT NULL,             -- sha256 of normalised body
  title              text NOT NULL,
  body               text NOT NULL,
  paragraphs         jsonb NOT NULL,            -- [{label:"A", text:"...", start:0, end:412}]
  word_count         int NOT NULL,
  target_band        numeric(2,1),
  cefr_level         text,
  readability        jsonb NOT NULL,            -- {flesch_kincaid, gunning_fog, ...}
  topic_id           uuid REFERENCES topics(id),
  genre              text,                      -- 'expository'|'argumentative'|'descriptive'
  created_by_run_id  uuid REFERENCES generation_runs(id),
  created_by_user_id uuid REFERENCES users(id), -- set on manual edit
  organization_id    uuid NOT NULL,             -- denormalised from passages, set by trigger
  change_note        text,
  created_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (passage_id, version_no),
  UNIQUE (organization_id, content_hash)        -- cheap exact-duplicate guard, tenant-scoped
)
```

`paragraphs` stores character offsets. This is what makes evidence spans verifiable: an answer can be
checked to lie inside the paragraph it claims to come from, deterministically.

### Content — items (questions)

```sql
items (
  id                 uuid PRIMARY KEY,
  organization_id    uuid NOT NULL REFERENCES organizations(id),
  module             text NOT NULL,
  item_type          text NOT NULL,             -- 'mcq_single'|'true_false_notgiven'|'heading_match'|...
  passage_id         uuid REFERENCES passages(id),   -- null for Writing/Speaking
  group_id           uuid,                      -- items answered as a block (e.g. one heading set)
  current_version_id uuid,
  status             text NOT NULL,
  created_at         timestamptz NOT NULL DEFAULT now()
)

item_versions (
  id                 uuid PRIMARY KEY,
  item_id            uuid NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  version_no         int NOT NULL,
  content_hash       text NOT NULL,
  stem               text NOT NULL,
  instructions       text,                      -- e.g. "NO MORE THAN TWO WORDS AND/OR A NUMBER"
  options            jsonb,                     -- [{key:"A", text:"..."}] — null for non-choice types
  answer_key         jsonb NOT NULL,            -- {type:"exact", values:["photosynthesis"], accept:[...]}
  evidence           jsonb,                     -- {paragraph:"C", start:1204, end:1279, quote:"..."}
  explanation        text,
  distractor_notes   jsonb,                     -- why each wrong option is wrong
  word_limit         int,
  difficulty         numeric(3,2),              -- 0..1, model estimate
  target_band        numeric(2,1),
  cefr_level         text,
  estimated_seconds  int,
  sequence_no        int,                       -- position within its passage/group
  quality_summary    jsonb,                     -- denormalised latest gate result, for fast listing
  created_by_run_id  uuid REFERENCES generation_runs(id),
  created_by_user_id uuid REFERENCES users(id),
  change_note        text,
  created_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (item_id, version_no)
)
```

**`evidence` is mandatory for every objectively-keyed type.** It is the single field that converts
answer-key checking from an LLM opinion into a string operation: for completion types the key must be
a verbatim substring of `passage_versions.body` at the stated offsets. This one design choice is
responsible for most of the trustworthy signal in the quality gate.

`answer_key.accept` holds legitimate alternates (`"1990s"` / `"the 1990s"`), so grading in IELTS
Ready is unambiguous and does not require fuzzy matching at test time.

### Quality

```sql
quality_checks (
  id                 uuid PRIMARY KEY,
  target_type        text NOT NULL,             -- 'passage_version' | 'item_version'
  target_id          uuid NOT NULL,
  run_id             uuid REFERENCES generation_runs(id),
  engine             text NOT NULL,             -- 'schema'|'rule'|'similarity'|'llm_critic'
  rule_code          text NOT NULL,             -- 'R-READ-001' — stable, referenced from code & docs
  severity           text NOT NULL,             -- 'must'|'should'|'info'
  passed             boolean NOT NULL,
  detail             jsonb,                     -- machine-readable evidence for the finding
  message            text,
  engine_version     text NOT NULL,             -- rules change; results must stay interpretable
  created_at         timestamptz NOT NULL DEFAULT now()
)
CREATE INDEX ON quality_checks (target_type, target_id);
CREATE INDEX ON quality_checks (rule_code) WHERE passed = false;

reviews (
  id                 uuid PRIMARY KEY,
  target_type        text NOT NULL,
  target_id          uuid NOT NULL,             -- always a *_version id
  reviewer_id        uuid NOT NULL REFERENCES users(id),
  decision           text NOT NULL,             -- 'approve'|'reject'|'request_changes'|'edit'
  reason_code        text,                      -- controlled vocabulary → trainable signal
  comment            text,
  time_spent_seconds int,                       -- feeds "reviewer minutes per approved item"
  created_at         timestamptz NOT NULL DEFAULT now()
)
```

`engine_version` matters: when a rule changes, historical results must remain interpretable. Without
it, "this item passed" is meaningless a year later.

`reason_code` is a controlled vocabulary, not free text. Rejection reasons accumulated over months are
the highest-quality training and prompt-improvement signal the system will ever produce — but only if
they are aggregatable.

### Vectors

```sql
embeddings (
  id                 uuid PRIMARY KEY,
  target_type        text NOT NULL,
  target_id          uuid NOT NULL,
  kind               text NOT NULL,             -- 'passage_body'|'item_stem'|'item_full'
  model_name         text NOT NULL,             -- mixed-model state must be detectable
  embedding          vector(768) NOT NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (target_type, target_id, kind, model_name)
)
CREATE INDEX ON embeddings USING hnsw (embedding vector_cosine_ops);
```

### Reference corpus — QUARANTINED

```sql
-- Authentic third-party material. Stored ONLY to prove our output does not overlap with it.
reference_documents (
  id                 uuid PRIMARY KEY,
  source             text NOT NULL,             -- 'cambridge_ielts_18' etc.
  licence_note       text NOT NULL,
  body               text NOT NULL,
  ngram_index        jsonb,                     -- MinHash signature
  created_at         timestamptz NOT NULL DEFAULT now()
)
```

> 🔒 **Hard rule.** Rows in `reference_documents` MUST NEVER be read by a generation agent, placed in
> a prompt, or used as a few-shot example. The only permitted consumer is the originality checker,
> which reads them to compute overlap against our own output. This is enforced by repository-level
> access control and a Cursor rule. See [Compliance](11-security-copyright-compliance.md).

### Assembly & publication

```sql
question_sets (
  id uuid PRIMARY KEY, organization_id uuid NOT NULL, module text NOT NULL,
  name text NOT NULL, spec jsonb NOT NULL, status text NOT NULL, created_at timestamptz
)

question_set_items (
  question_set_id uuid, item_version_id uuid, sequence_no int,
  PRIMARY KEY (question_set_id, item_version_id)
)
```

Note `question_set_items` references an **`item_version_id`, not an `item_id`.** A set pins the exact
content it was built from. Later edits to that item do not silently change an assembled test.

```sql
mock_tests (
  id uuid PRIMARY KEY, organization_id uuid NOT NULL, name text NOT NULL,
  exam text NOT NULL DEFAULT 'ielts', variant text,   -- 'academic'|'general'
  sections jsonb NOT NULL, status text NOT NULL, created_at timestamptz
)

-- The immutable artefact IELTS Ready consumes.
publications (
  id uuid PRIMARY KEY, mock_test_id uuid NOT NULL REFERENCES mock_tests(id),
  version_no int NOT NULL,
  snapshot jsonb NOT NULL,     -- fully denormalised, self-contained test payload
  snapshot_hash text NOT NULL,
  published_by uuid REFERENCES users(id),
  published_at timestamptz NOT NULL DEFAULT now(),
  revoked_at timestamptz, revoke_reason text,
  UNIQUE (mock_test_id, version_no)
)
```

**`snapshot` is fully denormalised on purpose.** A published test must be renderable without joining
live content tables. It cannot be affected by later edits, reviews or deletions anywhere in the
system. Consumers get an immutable, cacheable document. If a published test must be withdrawn we set
`revoked_at` — we never delete or mutate a snapshot.

### Prompts

```sql
prompt_versions (
  id uuid PRIMARY KEY,
  name text NOT NULL,              -- 'reading.passage.academic'
  version int NOT NULL,
  git_path text NOT NULL,          -- source of truth lives in the repo
  template_hash text NOT NULL,
  model_hint text, params jsonb,
  is_active boolean NOT NULL DEFAULT false,
  notes text, created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (name, version)
)
```

**Prompts live in git; the table mirrors them.** The dashboard's "prompt management" reads this table
and can activate/rollback versions, but authoring happens in files that get code review and diffs.
A database-only editable prompt blob destroys reproducibility and skips review — the two things this
system exists to guarantee.

---

## Lifecycle state machines

### Content item

```
                     ┌──────────────────────────────┐
                     ▼                              │
  draft ──▶ machine_checked ──▶ awaiting_review ──▶ needs_revision
              │                        │
              │ MUST-rule fail         ├──▶ approved ──▶ published ──▶ archived
              ▼                        │                    │
           blocked                     └──▶ rejected        └──▶ superseded
```

| State | Meaning |
|-------|---------|
| `draft` | Generated, not yet gated |
| `machine_checked` | Passed layers 0–3 |
| `blocked` | Failed a MUST rule. **Cannot be approved by a human.** Must be revised |
| `awaiting_review` | In the human queue |
| `needs_revision` | Reviewer requested changes |
| `approved` | Eligible for test assembly |
| `rejected` | Terminal. Retained as negative training signal — never deleted |
| `published` | Included in at least one publication |
| `superseded` | A newer version exists |
| `archived` | Withdrawn from use; retained |

**`blocked` cannot be overridden.** There is no "approve anyway" button. If a MUST rule is wrong, fix
the rule — with a test proving it — and re-run the gate. This keeps the rule engine honest: an
override button would turn every hard guarantee into a suggestion within a month.

### Generation run

```
queued ─▶ planning ─▶ generating ─▶ evaluating ─▶ revising ─┐
                                        ▲                   │
                                        └───────────────────┘  (max 2 loops)
                                        │
                            awaiting_review ─▶ completed
                                        │
   any state ─▶ failed  |  cancelled           partially_completed
```

`partially_completed` is a real, useful outcome: a 40-question request that yields 34 valid items is
a success worth keeping, not a failure worth discarding.

---

## Indexing plan

```sql
-- Review queue: the hottest operator query
CREATE INDEX idx_items_review_queue ON items (organization_id, status, created_at DESC)
  WHERE status IN ('awaiting_review','needs_revision');

-- Bank browsing / test building
CREATE INDEX idx_items_bank ON items (organization_id, module, item_type, status);
CREATE INDEX idx_iv_band ON item_versions (target_band, cefr_level);

-- Topic coverage analytics
CREATE INDEX idx_pv_topic ON passage_versions (topic_id, target_band);

-- Cost analytics
CREATE INDEX idx_ai_run_agent ON agent_invocations (run_id, agent);
CREATE INDEX idx_ai_created ON agent_invocations (created_at DESC);

-- Duplicate detection
CREATE INDEX idx_emb_hnsw ON embeddings USING hnsw (embedding vector_cosine_ops);
```

## Enforced invariants

Implemented as constraints and triggers, because "we agreed not to do that" is not an invariant:

1. **Version immutability** — `BEFORE UPDATE` trigger on `passage_versions` / `item_versions` raises.
   Only `items.current_version_id` moves.
2. **Monotonic versions** — `version_no` is assigned by trigger, never by the application.
3. **Approval requires a clean gate** — trigger rejects the transition to `approved` when any
   unresolved `severity='must'`, `passed=false` check exists for that version.
4. **Publication snapshots are frozen** — `publications` is insert-only except `revoked_at`.
5. **Tenant scoping** — every content query goes through a repository base class that requires an
   `organization_id`. Reviewed in CI by a lint rule.

## Migration discipline

- Every change is an Alembic migration. No manual DDL, ever, in any environment.
- Migrations are **forward-only** in production; roll forward with a fix rather than downgrade.
- Every migration that changes content tables ships with a data-integrity test.
- Migrations touching `*_versions` must preserve immutability triggers — there is a test for this.
