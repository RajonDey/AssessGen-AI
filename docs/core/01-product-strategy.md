# 01 — Product Strategy

## The problem

Producing high-quality IELTS practice content by hand is slow, expensive and inconsistent. A single
Academic Reading passage with 13 well-formed questions, verified answer keys and explanations is
several hours of skilled work. IELTS Ready needs this content continuously, in volume, across four
skill modules, at multiple band levels and across many topics.

Buying content is expensive and licence-encumbered. Copying it is illegal. Writing it in-house does
not scale. That is the gap this engine fills.

## The opportunity

The valuable asset is not "an IELTS question generator". It is a **general assessment content
engine** whose IELTS behaviour is one configurable pack. The same orchestration, quality gate,
versioning and export machinery serves TOEFL, PTE, GRE, SAT, school English exams and corporate
assessments — because the hard parts (workflow, quality control, calibration, provenance) are
format-independent.

Two business models follow from one codebase:

1. **Internal** — IELTS Ready consumes the engine's API for its own content supply.
2. **External** — other education companies consume the same API, or licence question packs, or run a
   white-labelled instance.

This is why the engine and the learning platform are separated at the API boundary from day one, even
though today there is exactly one consumer.

## Guiding principle

> **Do not train an LLM. Build an engineered system around one.**

Training a competitive model requires data, compute and expertise we do not have and do not need. The
defensible assets are:

| Asset | Why it is defensible |
|-------|---------------------|
| The quality rule engine | Encodes real IELTS format constraints; improves with every defect found |
| The calibration corpus | Human/authentic-material judgements that let us *prove* quality claims |
| The content database | Grows monotonically; versioned, tagged, deduplicated, reusable |
| Prompt + workflow lineage | Every item traceable to the exact prompt and model that made it |
| Provider independence | We can change model vendor without rewriting the product |

Model weights are a commodity and will keep getting cheaper and better. Everything in the table above
gets *more* valuable over time. That asymmetry is the strategy.

---

## Users and their jobs

| User | Job to be done | Primary surface |
|------|---------------|-----------------|
| **Content operator** (you, today) | Request generation in bulk; keep the bank growing | Admin dashboard → AI Generation |
| **Reviewer** | Judge whether an item is publishable; fix or reject fast | Admin dashboard → Review queue |
| **Test builder** | Assemble approved items into a coherent mock test | Admin dashboard → Test Builder |
| **Platform engineer** (IELTS Ready) | Fetch published tests reliably and immutably | Consumer REST API |
| **Analyst / owner** | Know cost, throughput, approval rate, coverage gaps | Admin dashboard → Analytics |

Today one person may hold all five roles. The system is still designed around the roles, because
that is what makes delegation and later multi-user operation possible without a rewrite.

---

## Scope

### In scope

- Generation of IELTS Academic and General Training content across Reading, Listening, Writing,
  Speaking.
- A layered quality gate with machine-checkable rules and human approval.
- Immutable, versioned content storage with full generation provenance.
- Mock test assembly, publication and export.
- An admin dashboard for generation, review, analytics and prompt management.
- A consumer API that IELTS Ready (and later, third parties) reads from.

### Explicitly out of scope (and why)

| Not doing | Reason |
|-----------|--------|
| Training or fine-tuning a foundation model | Cost and expertise are prohibitive; no evidence it beats prompting + rules |
| Student-facing UI, test delivery, scoring of student answers | That is IELTS Ready's job. The engine produces content, not experiences |
| Automated scraping of copyrighted exam material | Legal exposure; see [Compliance](11-security-copyright-compliance.md) |
| Real-time / interactive generation (sub-second) | Generation is a batch, human-reviewed activity. Latency budget is minutes |
| Claiming official IELTS endorsement | We are not affiliated with Cambridge/IDP/British Council. Never imply otherwise |

---

## Success metrics

Vanity metrics ("questions generated") are explicitly rejected. These are the numbers that matter:

### Tier 1 — is the content actually good?

| Metric | Definition | Target |
|--------|-----------|--------|
| **Human approval rate** | Approved ÷ submitted for review, first pass | ≥ 70 % by end of Phase 2 |
| **Rule-gate pass rate** | Items passing all MUST-level rules without revision | ≥ 85 % |
| **Post-approval defect rate** | Defects found after approval ÷ approved items | ≤ 2 % |
| **Rule engine false-positive rate** | Authentic IELTS items wrongly flagged by our rules | ≤ 5 % (see calibration below) |

### Tier 2 — is it economical?

| Metric | Definition | Target |
|--------|-----------|--------|
| **Reviewer minutes per approved item** | Total review time ÷ approved items | ≤ 3 min |
| **Cost per approved item** | Compute (or API) cost ÷ approved items | Tracked from day 1; no target until we have data |
| **Revision loops per approved item** | Mean critic→revise cycles | ≤ 2 |

### Tier 3 — is the bank useful?

| Metric | Definition | Target |
|--------|-----------|--------|
| **Coverage** | Populated cells in the topic × band × question-type matrix | ≥ 80 % of the target matrix |
| **Duplicate rate** | Items above the similarity threshold against an existing item | ≤ 1 % |
| **Reuse depth** | Approved items per published mock test that are newly generated | Decreasing over time |

**Cost per approved item is the metric that decides whether to buy a GPU server.** It is instrumented
from the first generation run, before we have any opinion about the answer.
See [Observability & Cost](12-observability-and-cost.md).

---

## Strategic risks

### ⚠️ Risk 1 — We cannot currently prove our content is good

**No qualified IELTS examiner is available to the team.** This is the most serious risk in the
project. An evaluator agent with no human ground truth does not measure quality; it produces
confident opinions that cannot be falsified. Shipping on that basis is how you get a bank of
thousands of plausible-looking, subtly wrong items — which is worse than having no bank, because the
errors are now expensive to find.

**Mitigation, in priority order:**

1. **Calibrate rules against authentic material.** Run the deterministic rule engine over real,
   published IELTS papers. Any rule that flags a genuine Cambridge item is a *bug in our rule*, not a
   defect in the paper. This gives us a real false-positive rate with zero examiner time, and is the
   highest-leverage action available. It is scheduled in Phase 1.
2. **Distribution matching.** Generated content should sit inside the same measurable distribution as
   authentic content (passage length, readability, answer-position spread, distractor overlap,
   question-type mix). Deviation is a signal even when we cannot say which item is wrong.
3. **Weak-supervision golden set.** The team labels 100–150 items carefully against published IELTS
   band descriptors and format specifications. Not examiner-grade, but it makes evaluator agreement
   *measurable* rather than assumed.
4. **Buy examiner time once.** A single paid review pass over ~100 items by a certified examiner
   would convert items 1–3 from proxies into validated ground truth. This remains the recommended
   purchase and is tracked in [Open Questions](../execution/open-questions.md).

Until at least steps 1–3 are done, **no quality claim leaves the building.** Internal scores are
labelled as internal heuristics, never as band-accuracy guarantees.

### ⚠️ Risk 2 — Local model quality ceiling

Development runs entirely on local models to avoid API cost. On 16 GB of unified memory the practical
ceiling is a ~9 B parameter model at 4-bit quantisation. That is capable enough to prove the *pipeline*
works, and probably not capable enough to produce Band 8-quality Academic Reading passages reliably.

**Mitigation:** the LLM gateway is provider-agnostic from the first commit, model choice is
configuration per agent role, and a benchmark harness scores any model on identical tasks. The
production model decision is deliberately deferred until that harness produces evidence.
See [LLM Gateway & Local Models](07-llm-gateway-and-local-models.md).

### ⚠️ Risk 3 — Copyright contamination

Using authentic IELTS books as prompt examples risks the model reproducing protected expression in
supposedly original output. See [Compliance](11-security-copyright-compliance.md) for the firewall
design. Summary: authentic material informs *structure and statistics*, never *expression*, and is
stored solely to run negative-overlap checks against our own output.

### ⚠️ Risk 4 — Scope dilution

The Phase 1 decision is to touch all four modules rather than perfect one. This risks four
half-finished pipelines and no proven quality loop.

**Mitigation:** Phase 1 is explicitly structured as *shared spine + four thin verticals*, with the
full quality loop proven end-to-end on Reading only. The other three modules reach
generate→store→review depth and inherit the loop in Phase 2. Reading is the reference implementation;
its rule engine is the template the others copy. See [Roadmap](../execution/roadmap.md).

---

## Non-negotiable principles

1. **Nothing is published without passing the gate.** No manual back door to the published state.
2. **Nothing is ever overwritten.** Edits create versions; publications create frozen snapshots.
3. **Every item knows its parents** — the run, the prompt version, the model, the seed, the settings.
4. **The engine knows nothing about IELTS Ready.** Coupling flows one way, through the public API.
5. **Deterministic checks outrank model opinion.** When a rule and the critic disagree, the rule wins.
6. **Human review is a scarce resource.** Design to reduce reviewer load, never to bypass review.
