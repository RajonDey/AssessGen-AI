# Open Questions

Decisions that are still open, who owns them, and — critically — **when they must be answered**. A
question with no deadline is a question that gets answered by accident.

---

## Blocking — must be resolved before or during Phase 1

### Q1 — Examiner validation ★

**Question:** Will we buy one certified IELTS examiner review pass (~100 items, roughly one day)?

**Why it matters.** This is the highest-value open item in the project. Without it, every band claim
we make is an estimate, and we cannot sell content, licence the API, or truthfully tell a learner
that a "Band 7 model answer" is Band 7. The calibration methods in
[Quality & Evaluation](../core/08-quality-and-evaluation.md) are good proxies designed specifically to
work without an examiner — but they are proxies, and they validate *structure*, not *judgement*.

**Cost:** roughly one day of expert time. **Value:** converts four proxy methods into validated
ground truth and unblocks any external commercial use.

**Deadline:** decide by end of Phase 1; required before Phase 4.
**Owner:** you.

### Q2 — Authentic material inventory

**Question:** Exactly which IELTS papers do we hold, and under what terms?

**Why it matters.** Calibration (Method 1) needs at least 3–5 complete authentic papers. The
originality corpus needs as much authentic text as we can legitimately hold. The
[compliance firewall](../core/11-security-copyright-compliance.md) requires the licence terms to be
recorded per document.

**Needed:** a list of sources, formats (print/PDF/digital) and licence notes.
**Deadline:** Phase 1B, before calibration.
**Owner:** you.

### Q3 — Target volume

**Question:** How many approved items per week does IELTS Ready actually need?

**Why it matters.** Every capacity decision depends on it — the hardware purchase, the review sampling
policy, the queue design. The current dev machine supports roughly 25–30 approved items/day at a 50 %
approval rate. Whether that is comfortable or hopeless is entirely a function of this number, and
without it the Phase 2 hardware checkpoint cannot be evaluated.

**Deadline:** before the Phase 2 hardware checkpoint.
**Owner:** you.

---

## Important — resolve during Phase 2

### Q4 — Production model

**Question:** Local 9 B, a larger self-hosted model on purchased hardware, or a cloud API?

**Status:** deliberately deferred; the gateway makes the deferral real. The benchmark harness (Phase
1D) and cost report (Phase 2) exist specifically to answer it with data.

**Decision rule** is written down in
[LLM Gateway & Local Models](../core/07-llm-gateway-and-local-models.md) — including the important
distinction that if local *quality* is far behind, faster hardware does not help.

**Deadline:** end of Phase 2. **Owner:** you, with benchmark data.

### Q5 — Accent coverage for Listening

**Question:** Kokoro provides British and American English. IELTS also uses Australian and New Zealand
accents. Do we ship with the gap, or find another solution?

**Options:** ship and disclose the limitation; find an additional Apache/MIT-licensed TTS with those
accents; use Chatterbox (MIT) with cloning from licensed voice samples; commission recordings.

**Deadline:** Phase 3, before Listening audio ships. **Owner:** you.

### Q6 — Similarity thresholds

**Question:** The duplicate thresholds (0.95 reject, 0.88 flag) are estimates.

**Resolution:** tune against real data once a few thousand items exist. Requires a labelled sample of
true and false duplicates.

**Deadline:** Phase 2. **Owner:** engineering, with review data.

### Q7 — Band-to-readability mapping

**Question:** What Flesch-Kincaid and vocabulary-frequency ranges correspond to each IELTS band?

**Resolution:** derive from authentic papers via distribution matching (Method 2). Until then,
`target_band` is an unvalidated intent and is labelled as such in the UI.

**Deadline:** Phase 1B calibration. **Owner:** engineering.

---

## Deferred — Phase 3+

### Q8 — Deployment target
Where does this run in production? Options: a VPS with Docker Compose, a managed platform (Railway,
Fly.io, Render), or cloud VMs. Interacts with Q4 — self-hosting a large model constrains the choice
substantially. *Deadline: Phase 3.*

### Q9 — Multi-tenancy depth
The schema carries `organization_id` from day one. Full SaaS (roles, billing, RLS, white-label) is
Phase 4 and depends on real external demand. *Deadline: Phase 4 kickoff.*

### Q10 — Adaptive testing
The original vision mentions adaptive difficulty and personalised test generation. This is
**IELTS Ready's** responsibility, not the engine's — the engine supplies well-tagged items with
difficulty metadata; selection logic belongs in the platform. Confirm this boundary before either side
builds it. *Deadline: Phase 3.*

### Q11 — Second exam format
Which exam validates the "engine, not IELTS tool" claim — TOEFL, PTE, or a school English exam? Doing
one is what proves the abstraction; until then it is an assertion. *Deadline: post-Phase 3.*

---

## Resolved

| # | Question | Decision | Where |
|---|----------|----------|-------|
| R1 | Train a model or build around one? | Build around commodity LLMs | [Strategy](../core/01-product-strategy.md) |
| R2 | Local or cloud for dev? | Local, with a provider-agnostic gateway | [ADR-0004](../decisions/ADR-0004-llm-gateway.md) |
| R3 | Evaluator design | Deterministic rules first; critic emits findings, never a score | [ADR-0002](../decisions/ADR-0002-quality-gate-ordering.md) |
| R4 | Tenancy | `organization_id` from day one; SaaS features deferred | [ADR-0005](../decisions/ADR-0005-tenancy-hedge.md) |
| R5 | Phase 1 scope | Shared spine + Reading deep + three thin verticals | [Roadmap](roadmap.md) |
| R6 | Frontend | One Next.js 16 admin app; FastAPI backend | [Tech Stack](../core/03-tech-stack.md) |
| R7 | Authentic material use | Structure and statistics only; text quarantined for negative checks | [Compliance](../core/11-security-copyright-compliance.md) |
| R8 | Vector store | pgvector in the same Postgres | [ADR-0003](../decisions/ADR-0003-pgvector.md) |
| R9 | Content versioning | Immutable versions; frozen publication snapshots | [ADR-0001](../decisions/ADR-0001-immutable-versioning.md) |
| R10 | TTS engine | Kokoro (Apache 2.0); XTTS rejected on licence | [Listening](../modules/listening.md) |
