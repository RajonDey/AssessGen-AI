# AssessGen AI — Documentation

An **AI Assessment Content Engine**: a system that generates, validates, improves, versions and
exports assessment content. IELTS is the first target; the engine is deliberately not IELTS-only.

> **Status:** Phase 1A complete; **Phase 1B (Reading) complete in code**; **Phase 1C in progress.**
> Application code lives in `backend/`. These documents are the contract we build against.

**New here?** Install from the [repository README](../README.md). The longer guide is [Installation](installation.md) (requirements, Ollama, env, TTS).

---

## The one-paragraph version

We are **not training a model**. We are building an engineered system *around* commodity LLMs, where
the durable value lives in the workflow, the quality-control logic, the calibration data and the
content database — not in model weights. A generation request enters through an API, is planned and
executed as a LangGraph workflow, produces candidate content, and then must survive a layered quality
gate (schema → deterministic rules → originality → LLM critic → human review) before it can be
published. Everything is versioned and immutable; nothing is ever overwritten.

---

## Modular development — confirmed

Yes. The plan is **modular by design**, not a single monolithic blob of code. Three kinds of modularity
work together:

| Kind | What it means | Where it lives |
|------|---------------|----------------|
| **Layer modularity** | Six strict layers (api → services → workflows → agents → domain → infrastructure). Dependencies point downward only | [System Architecture](core/02-system-architecture.md) |
| **Exam-pack modularity** | IELTS is one pack under `app/modules/ielts/`. Adding TOEFL = one new directory, no core changes | [Folder Structure](core/06-folder-structure.md) |
| **Deploy modularity** | One deployable **modular monolith** (not microservices). Workers share the same codebase | [ADR-0006](decisions/ADR-0006-modular-monolith.md) |

Within each pack, work is further split: one file per quality rule, versioned prompt files, shared
workflow nodes, and type-specific schemas. **import-linter enforces boundaries in CI** — modular style
is structural, not a convention we hope people follow.

Phase 1 follows the same pattern: build the **shared spine once**, then plug in Reading (deep) and
Listening / Writing / Speaking (thin verticals) on the same rails.
→ [Execution Roadmap](execution/roadmap.md)

---

## Read in this order

### Core (read all of these before writing code)

| # | Document | What it decides |
|---|----------|-----------------|
| 01 | [Product Strategy](core/01-product-strategy.md) | Why this exists, who uses it, what "done" means, what we refuse to do |
| 02 | [System Architecture](core/02-system-architecture.md) | The blueprint: components, boundaries, data flow, failure modes |
| 03 | [Tech Stack](core/03-tech-stack.md) | Confirmed stack with pinned versions, and what we rejected |
| 04 | [Data Model](core/04-data-model.md) | Schema, immutable versioning, content lifecycle state machine |
| 05 | [API Design](core/05-api-design.md) | REST contract, async job pattern, consumer API |
| 06 | [Folder Structure](core/06-folder-structure.md) | Repository layout and module boundaries |
| 07 | [LLM Gateway & Local Models](core/07-llm-gateway-and-local-models.md) | Provider abstraction, the 16 GB memory budget, model roles |
| 08 | [Quality & Evaluation](core/08-quality-and-evaluation.md) | **The most important document.** How we know content is good |
| 09 | [Testing & QA](core/09-testing-and-qa.md) | Test strategy, the eval harness, CI gates |
| 10 | [Dependencies](core/10-dependencies.md) | Every dependency, pinned and justified |
| 11 | [Security, Copyright & Compliance](core/11-security-copyright-compliance.md) | Auth, tenancy, and the copyright firewall |
| 12 | [Observability & Cost](core/12-observability-and-cost.md) | Tracing, metrics, and the data that decides the server purchase |

### Modules (read when you build that module)

- [Reading](modules/reading.md) — the reference implementation; build this first
- [Listening](modules/listening.md) — dialogue → questions → TTS → audio QA
- [Writing](modules/writing.md) — Task 1 / Task 2 with band-differentiated model answers
- [Speaking](modules/speaking.md) — Parts 1–3 with band-differentiated sample responses
- [Paper spec](modules/paper-spec.md) — per-part topics + interlocking type plans (BC-style)

### Decisions & execution

- [Installation](installation.md) — system requirements, `requirements.txt`, Ollama, admin UI, TTS
- [Architecture Decision Records](decisions/) — why we chose what we chose, and what would reverse it
- [Execution Roadmap](execution/roadmap.md) — phased delivery plan
- [Phase 1A — Foundation](execution/phase-1a-foundation.md) — backend spine (complete)
- [Phase 1B — Reading](execution/phase-1b-reading.md) — Reading end-to-end (complete in code)
- [Phase 1C — Thin verticals](execution/phase-1c-thin-verticals.md) — Listening, Writing, Speaking (**current**)
- [Phase 1D — Benchmark](execution/phase-1d-benchmark.md) — model comparison harness (next)
- [Phase 1 checklist](execution/phase-1-checklist.md) — master tracker; update when sub-phases complete
- [Open Questions](execution/open-questions.md) — what is still undecided and who must decide it

---

## Five things that are easy to get wrong

These are the failure modes this design exists to prevent. If you disagree with one, read the linked
document before changing anything.

1. **A quality score is not quality.** An LLM grading content produced by a comparable LLM inflates
   its own results. Our numeric confidence comes from *deterministic rules first*; the LLM critic
   produces structured findings, never a headline score.
   → [Quality & Evaluation](core/08-quality-and-evaluation.md)

2. **"AI-generated" does not mean "copyright-free."** Models reproduce training data. Original output
   is something we *verify*, not something we assume.
   → [Security, Copyright & Compliance](core/11-security-copyright-compliance.md)

3. **The dev machine has 16 GB of unified memory.** Two large models cannot be resident at once.
   Concurrency is bounded by a global model lease, not by worker count.
   → [LLM Gateway & Local Models](core/07-llm-gateway-and-local-models.md)

4. **Content is immutable.** Approved content is never mutated in place. Edits create a new version;
   publication creates a frozen snapshot. A student's completed test must remain reproducible years
   later.
   → [Data Model](core/04-data-model.md)

5. **The engine is the product; IELTS Ready is a client of it.** No IELTS-specific logic may leak into
   the orchestration, gateway or storage layers. It belongs in module packs.
   → [System Architecture](core/02-system-architecture.md)

---

## Conventions used in these docs

- **MUST / SHOULD / MAY** carry their RFC 2119 meanings. MUST-level rules are enforced in code review
  and, where possible, in CI.
- Rule identifiers such as `R-READ-001` are stable and referenced from code, tests and database rows.
- `⚠️ Risk` marks a known unresolved risk, not a task.
- Version numbers in these documents were verified against package registries on 2026-07-30.
