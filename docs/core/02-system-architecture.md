# 02 — System Architecture (The Blueprint)

## Architectural goals, in priority order

When two goals conflict, the higher one wins. This ordering is the single most useful thing in this
document.

1. **Content correctness** — a wrong answer key is worse than no content.
2. **Provenance & reproducibility** — every artefact traceable to its inputs, forever.
3. **Provider independence** — swapping the model must not touch agent or domain code.
4. **Operator throughput** — minimise human review minutes per approved item.
5. **Extensibility to non-IELTS exams** — new formats are packs, not forks.
6. **Raw generation speed** — deliberately last. This is a batch system.

---

## System context

```
        ┌──────────────────┐          ┌─────────────────────┐
        │  Content operator │          │  Reviewer / builder │
        └─────────┬─────────┘          └──────────┬──────────┘
                  │                                │
                  └────────────┬───────────────────┘
                               ▼
                  ┌────────────────────────┐
                  │   Admin Dashboard      │  Next.js 16 (internal, authenticated)
                  └───────────┬────────────┘
                              │ HTTPS / JSON
                              ▼
   ┌───────────────────────────────────────────────────────────┐
   │            ASSESSGEN AI ENGINE  (this system)             │
   └───────────┬───────────────────────────────┬───────────────┘
               │ consumer API                  │ inference
               ▼                               ▼
   ┌────────────────────────┐      ┌──────────────────────────┐
   │  IELTS Ready platform  │      │  Model runtime           │
   │  (external consumer)   │      │  Ollama (local) │ Cloud  │
   └────────────────────────┘      └──────────────────────────┘
```

The engine has exactly **one** outbound dependency on a model runtime, mediated entirely by the LLM
Gateway. It has **zero** knowledge of IELTS Ready — the platform pulls from the consumer API.

---

## Layered architecture

Dependencies point **downward only**. A layer may import from layers below it and never from layers
above. This is enforced by an import-linter contract in CI (see [Testing & QA](09-testing-and-qa.md)).

```
┌────────────────────────────────────────────────────────────────────┐
│ L6  INTERFACE            FastAPI routers · Admin UI · CLI          │
│                          HTTP concerns only. No business logic.    │
├────────────────────────────────────────────────────────────────────┤
│ L5  APPLICATION          Use-case services · job dispatch          │
│                          Transaction boundaries. Orchestrates L4.  │
├────────────────────────────────────────────────────────────────────┤
│ L4  ORCHESTRATION        LangGraph workflows · human interrupts    │
│                          The state machine of a generation run.    │
├────────────────────────────────────────────────────────────────────┤
│ L3  AGENTS               Planner · Generators · Critic · Reviser   │
│                          One responsibility each. Stateless.       │
├────────────────────────────────────────────────────────────────────┤
│ L2  DOMAIN               Item/passage models · rule engine ·       │
│                          lifecycle · scoring. Pure Python, no I/O. │
├────────────────────────────────────────────────────────────────────┤
│ L1  INFRASTRUCTURE       LLM gateway · repositories · vector store │
│                          object storage · TTS · queue              │
└────────────────────────────────────────────────────────────────────┘
```

**Why L2 is pure.** The rule engine is where correctness lives. Keeping it free of I/O means it runs
in microseconds, is trivially unit-testable, is deterministic, and can be executed against thousands
of authentic IELTS items during calibration without touching a database or a model. This constraint
is load-bearing — do not relax it for convenience.

---

## Components

### Assessment Orchestrator (L4)

A LangGraph `StateGraph` per module. It owns run state, retries, branching and the human-approval
pause. State is persisted with `PostgresSaver` so a paused run survives a process restart — a paused
approval is a database row, not a live process.

Human approval uses LangGraph's `interrupt()` primitive rather than a hand-rolled polling mechanism.
When a node calls `interrupt()`, the graph serialises state and returns control; the run resumes via
`Command(resume=...)` against the same `thread_id`. `thread_id` is the run ID and is treated as a
recovery key.

> **Version note:** LangGraph is on the v1 LTS line. Most tutorials online are 0.x and use APIs that
> have changed. See [Tech Stack](03-tech-stack.md) and the installed `langgraph-persistence` and
> `langgraph-human-in-the-loop` skills in `.agents/skills/`.

**Durability mode:** `"sync"` for generation graphs. These runs are long and expensive; losing an
in-flight run to a crash costs more than the checkpoint write overhead.

### Agents (L3)

Every agent obeys the same contract:

```
typed Pydantic input  →  agent  →  typed Pydantic output + AgentTrace
```

Agents are **stateless**, **individually testable**, and **never touch the database directly**. They
receive what they need and return structured data. An agent that needs persistence is a design error.

| Agent | Responsibility | Notes |
|-------|---------------|-------|
| **Planner** | Turn a request into a concrete work plan (sections, difficulty spread, type mix) | Must be deterministic-checkable: the plan is validated against module rules before any generation |
| **Passage Generator** | Produce original source text | Reading passages, Listening dialogue scripts |
| **Question Generator** | Produce items from source text | Type-specific prompts and output schemas |
| **Answer Generator** | Produce answer key + evidence span + explanation | **Evidence span is mandatory** — it is what makes the key machine-verifiable |
| **Critic** | Find defects; emit structured findings | Emits findings, **never a headline score**. Runs on a different model/prompt from the generator |
| **Reviser** | Repair specific findings | Receives findings, not free-form "make it better" |
| **Metadata Agent** | Topic, tags, CEFR, estimated time | Cheap model; deterministic fallbacks |

**The Evaluator is not an agent.** It is the deterministic rule engine in L2. This is the most
important structural decision in the system — see [Quality & Evaluation](08-quality-and-evaluation.md).

### Quality Gate (L2 + L3)

Five layers, executed in order. **Cheap and certain before expensive and fuzzy.**

```
  candidate content
        │
        ▼
  [0] Schema validation        Pydantic. Malformed output never reaches the DB.
        │                      Fails → immediate regenerate, no cost downstream.
        ▼
  [1] Deterministic rules      Pure functions. Verbatim answer match, word limits,
        │                      option uniqueness, counts, readability, key spread.
        │                      MUST-level failure → blocked. Cannot be overridden.
        ▼
  [2] Originality & dedup      n-gram overlap vs quarantined reference corpus;
        │                      pgvector similarity vs our own bank.
        ▼
  [3] LLM critic               Structured findings only. Ambiguity, weak distractors,
        │                      register mismatch, multiple defensible answers.
        ▼
  [4] Human review             Sampled, not exhaustive. Rate depends on the item's
        │                      machine-check profile.
        ▼
  approved → publishable
```

Layers 0–2 are free, fast and trustworthy. Layer 3 is slow and unreliable. Layer 4 is the scarcest
resource in the system. Ordering them this way means the expensive layers only ever see content that
has already survived the cheap ones.

### LLM Gateway (L1)

The single choke point for all model calls. Nothing else in the codebase may import a provider SDK.

Responsibilities:

- **Role-based routing** — callers ask for a *role* (`generator`, `critic`, `metadata`, `embedding`),
  never a model name. Role→model mapping is configuration.
- **Model leasing** — a global semaphore that bounds concurrent resident models. On a 16 GB machine
  this is what prevents memory thrashing. See [LLM Gateway](07-llm-gateway-and-local-models.md).
- **Structured output** — JSON-schema-constrained generation with a repair-and-retry loop.
- **Accounting** — tokens, wall time, tokens/sec and cost recorded per call, local or cloud.
- **Determinism capture** — seed, temperature, top_p, model digest and prompt hash recorded on every
  call so any generation can be re-run.

This is what makes "defer the production model decision" a real option rather than a wish.

### Workers & queue (L1/L5)

Celery over Redis for job dispatch, scheduling and bulk fan-out. LangGraph handles in-graph state and
step-level recovery.

**The boundary must stay crisp, or you get double-retry bugs:**

| Concern | Owner |
|---------|-------|
| "Run this job later / in bulk / on a schedule" | Celery |
| "Retry the whole run after infrastructure failure" | Celery |
| "What step are we on, and what happened in it" | LangGraph checkpointer |
| "Retry this node / branch on this condition" | LangGraph |
| "Pause for a human, possibly for days" | LangGraph `interrupt()` |

Celery MUST NOT retry a run that failed inside a graph node for content reasons. Content failure is a
result, not an error.

**Queues are split by resource profile**, because they contend for different things:

- `q.generate` — GPU/model-bound. Concurrency **1** on the dev machine.
- `q.audio` — CPU-bound TTS. Concurrency 2.
- `q.io` — exports, embeddings, webhooks. Concurrency 4.

### Storage (L1)

| Store | Holds | Why |
|-------|-------|-----|
| PostgreSQL 18 | All content, versions, runs, reviews, checkpoints | One transactional source of truth |
| pgvector 0.8.6 | Embeddings for dedup and retrieval | Same database — no sync problem, joins work |
| S3 / Cloudflare R2 | Audio, images, exported PDFs | Binary blobs do not belong in Postgres |
| Redis | Celery broker, cache, rate limits | Ephemeral only. **Never** the sole owner of state |

Using pgvector rather than a dedicated vector database is deliberate: our vector workload is small
(hundreds of thousands of items at most), and keeping vectors transactionally consistent with content
is worth far more than the recall/latency advantage of a specialised store at this scale.

---

## Primary data flow — a generation run

```
1.  POST /api/v1/generation/reading  { band, topic, counts, idempotency-key }
        │
2.  Application service validates request, creates GenerationRun (status=queued),
    returns 202 + run_id.  ← client is never blocked
        │
3.  Celery picks up the job on q.generate
        │
4.  LangGraph run begins; thread_id = run_id; checkpoint written each step
        │
5.  Planner → plan;  plan validated against module rules  ──fail──▶ replan (max 2)
        │
6.  Passage Generator → passage draft
        │
7.  Quality layers 0–2 on the passage  ──MUST fail──▶ regenerate (max 2) ──▶ run fails cleanly
        │
8.  Question Generator → items   (batched by question type)
9.  Answer Generator  → keys + evidence spans + explanations
        │
10. Quality layers 0–2 on each item
        │
11. Critic → structured findings
        │
12. Any blocking finding? ──yes──▶ Reviser → back to step 10   (max 2 loops)
        │ no
13. Persist: passage_version + item_versions + quality_checks + embeddings
    Status → awaiting_review
        │
14. interrupt()  ← graph pauses; state is a Postgres row. May wait days.
        │
15. Reviewer approves/rejects/edits in the dashboard
        │
16. POST /runs/{id}/resume → Command(resume=decision)
        │
17. Approved content → status=approved, available to the Test Builder
```

**Steps 5, 7, 12 are bounded loops.** Every loop in this system has a hard iteration cap and a
defined give-up state. An unbounded "revise until quality threshold" loop is a cost and latency
hazard: with a weak local model it may never converge, and it will happily burn an afternoon trying.
When a cap is hit the run **fails loudly with its findings attached** rather than silently
downgrading quality.

---

## Extensibility: how a second exam format is added

This is the test of whether the architecture achieved its stated goal. Adding TOEFL must require:

```
backend/app/modules/toefl/
    spec.py         format constants, section structure, timing
    rules/          deterministic rules (TOEFL-specific)
    prompts/        versioned prompt templates
    schemas.py      Pydantic item shapes
    graph.py        LangGraph workflow (usually composed from shared nodes)
```

and **no change** to: the gateway, the orchestrator runtime, the storage schema, the review workflow,
the API shape, or the dashboard shell. If a new format forces a change in any of those, the
abstraction is wrong and should be fixed rather than worked around.

Concretely, this means the core schema stores `module`, `item_type` and `spec_version` as data, not as
enums baked into table structure, and the dashboard renders items from a type registry rather than
hard-coded components.

---

## Failure modes and responses

| Failure | Detection | Response |
|---------|-----------|----------|
| Model returns unparseable JSON | Pydantic validation (L0) | Repair prompt, then retry ×2, then fail the node |
| Model unreachable / OOM | Gateway health check | Fail fast; Celery retries with backoff; alert |
| MUST-rule violation after max revisions | Rule engine | Run fails with findings attached; nothing persisted as approved |
| Duplicate content detected | pgvector similarity | Reject item, log, do not count toward quota |
| Overlap with reference corpus | n-gram check | **Hard block.** Quarantine, alert, never publishable |
| Worker crashes mid-run | Celery + checkpoint | Resume from last checkpoint via `thread_id` |
| Reviewer never responds | Queue age monitor | Run stays paused indefinitely — this is correct behaviour, surfaced as a stale-queue metric |
| Two workers load models simultaneously | Model lease semaphore | Second worker blocks until lease is free |
| Prompt regression ships | Eval harness in CI | Block merge on golden-set regression |

---

## What is deliberately *not* in the architecture

- **A microservice split.** This is a modular monolith. One deployable backend, clear internal
  boundaries. At this scale and team size, service boundaries would add distributed-systems failure
  modes and buy nothing. The layer contract keeps a future split cheap if it is ever justified.
- **A dedicated vector database.** See Storage above.
- **A workflow engine (Temporal/DBOS).** LangGraph's Postgres checkpointer covers our durability
  needs. Revisit only if we need multi-day, multi-approver, compensating workflows.
- **A message bus / event sourcing.** The generation-run and version tables already provide the audit
  trail that event sourcing would give us, without the read-model complexity.
- **GraphQL.** One primary consumer, resource-shaped data, and a strong need for cacheable immutable
  reads. REST fits better.

Each of these is recorded with reversal criteria in [decisions/](../decisions/).
