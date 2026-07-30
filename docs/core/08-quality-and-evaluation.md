# 08 — Quality & Evaluation

> This is the most important document in the project. The generation pipeline is commodity
> engineering; anyone can wire an LLM to a database. **The quality system is the product.**

---

## The problem with the original design

The original plan had an Evaluator Agent that returns:

```
Overall
92/100
```

That number cannot be trusted, for three independent reasons.

**1. Self-evaluation bias.** An LLM scoring content produced by a comparable LLM systematically
inflates its judgement. The reasoning that produced an error also endorses it — the model is blind to
exactly the failures it just committed. On a 9 B local model this effect is severe.

**2. The number is unfalsifiable.** What would prove that 92 is wrong? Without ground truth there is
no answer, so the score cannot be improved, only regenerated. A metric that cannot be wrong cannot be
useful.

**3. It collapses distinct failures into one dimension.** "Answer key is factually wrong" and
"distractor is slightly weak" are not the same kind of problem and must not average together. One is
a hard block; the other is a note for a reviewer. A single number hides that difference precisely
when it matters most.

### The replacement

```
Deterministic rules produce verdicts.        ← certain, cheap, falsifiable
LLM critics produce findings.                ← useful, uncertain, never a score
Humans produce decisions.                    ← authoritative, scarce
```

Where a rule and the critic disagree, **the rule wins**. Where a human and a rule disagree, the human
must fix the rule — with a test — rather than override it.

---

## The five layers

```
 generated content
        │
 ┌──────▼──────────────────────────────────────────────────────┐
 │ L0  SCHEMA           Pydantic. Microseconds. Malformed       │
 │                      output never reaches the database.      │
 ├──────────────────────────────────────────────────────────────┤
 │ L1  DETERMINISTIC    Pure functions. Milliseconds.           │
 │     RULES            ~90 % of real defects caught here.      │
 │                      MUST failures are absolute blocks.      │
 ├──────────────────────────────────────────────────────────────┤
 │ L2  ORIGINALITY      n-gram overlap vs reference corpus;     │
 │     & DEDUP          pgvector similarity vs our own bank.    │
 ├──────────────────────────────────────────────────────────────┤
 │ L3  LLM CRITIC       Seconds and real cost. Structured       │
 │                      findings only. Catches semantic issues  │
 │                      rules cannot express.                   │
 ├──────────────────────────────────────────────────────────────┤
 │ L4  HUMAN REVIEW     Minutes. The scarcest resource.         │
 │                      Sampled, not exhaustive.                │
 └──────────────────────────────────────────────────────────────┘
```

The ordering is the design. Each layer is orders of magnitude more expensive than the one above, so
each must only ever see content that survived the cheaper layers. Running the critic on content with
a malformed answer key wastes money to discover something a string comparison already knew.

---

## L1 — The deterministic rule engine

### Why this layer carries the system

Most IELTS format requirements are **objectively checkable**. "The answer must be no more than two
words and must appear verbatim in the passage" is not a matter of opinion — it is a string operation.
Every requirement of that kind that we express as a rule is a defect class permanently eliminated,
with no model, no cost and no uncertainty.

Rules are pure functions over content, in `domain/` and `modules/`, with no I/O.

```python
class RuleResult(BaseModel):
    rule_code: str          # 'R-READ-001'
    passed: bool
    severity: Severity      # must | should | info
    message: str
    detail: dict            # machine-readable evidence
```

`detail` matters as much as `passed`: the dashboard highlights the offending span in the passage, so
a reviewer sees the problem rather than reading a description of it.

### Severity

| Severity | Meaning | Effect |
|----------|---------|--------|
| `must` | Objectively invalid; violates the exam format or is internally inconsistent | **Blocks.** Cannot be approved by anyone. Must be revised |
| `should` | Probably a quality problem; some legitimate exceptions exist | Surfaced to the reviewer, does not block |
| `info` | Observation for analytics | Recorded only |

**There is no override for `must`.** If a MUST rule is wrong, fix the rule and ship a test that proves
it. An "approve anyway" button turns every hard guarantee into a suggestion within about a month —
and the guarantees are the only reason the output can be trusted.

### Reading rules (the reference set)

These are the concrete rules to implement first. Reading is the template every other module copies.

#### Passage rules

| Code | Severity | Check |
|------|----------|-------|
| `R-PASS-001` | must | Word count within module bounds (Academic: 700–1000) |
| `R-PASS-002` | must | Paragraph labels are sequential and unique (A, B, C…) |
| `R-PASS-003` | must | No placeholder/meta text ("as an AI", "Passage:", "[insert]", "In this essay I will") |
| `R-PASS-004` | should | Readability within the target band's range (Flesch-Kincaid, via `textstat`) |
| `R-PASS-005` | should | Vocabulary profile matches target CEFR (`wordfreq` frequency bands) |
| `R-PASS-006` | should | Sentence-length variance above a floor — flat rhythm reads as machine-written |
| `R-PASS-007` | must | No first/second-person address ("you will learn") in Academic passages |
| `R-PASS-008` | should | Paragraph count appropriate to the question types (heading matching needs ≥ 6) |
| `R-PASS-009` | must | No factual self-contradiction between stated figures/dates |

#### Universal item rules

| Code | Severity | Check |
|------|----------|-------|
| `R-ITEM-001` | must | Stem is non-empty and above a minimum length |
| `R-ITEM-002` | must | Stem does not contain the answer verbatim (**answer leakage**) |
| `R-ITEM-003` | must | An answer key exists and is well-formed for the item type |
| `R-ITEM-004` | must | Evidence span exists and its offsets lie inside the passage |
| `R-ITEM-005` | must | The quoted evidence matches the passage text at those offsets |
| `R-ITEM-006` | should | No near-duplicate stem within the set (rapidfuzz ≥ 0.9) |
| `R-ITEM-007` | should | Estimated time within a plausible range for the type |
| `R-ITEM-008` | must | Instructions match the item type (word limit present iff completion type) |

#### Completion types (sentence / summary / short answer / table / diagram)

| Code | Severity | Check |
|------|----------|-------|
| `R-COMP-001` | **must** | **The answer is a verbatim, contiguous, case-insensitive substring of the passage** |
| `R-COMP-002` | must | Answer word count obeys the stated limit ("NO MORE THAN TWO WORDS AND/OR A NUMBER") |
| `R-COMP-003` | must | The stated limit is one of the legal IELTS phrasings |
| `R-COMP-004` | should | Accepted alternates are genuinely equivalent, not merely similar |
| `R-COMP-005` | must | The gap position produces a grammatical sentence when filled |
| `R-COMP-006` | should | The answer is not a function word (a, the, of, and) |

`R-COMP-001` alone eliminates the single most common and most damaging generation failure: a
paraphrased answer that a real candidate could never produce. It costs one `str.find()`.

#### True / False / Not Given

| Code | Severity | Check |
|------|----------|-------|
| `R-TFNG-001` | must | Answer is exactly one of TRUE / FALSE / NOT GIVEN |
| `R-TFNG-002` | must | TRUE and FALSE items carry an evidence span; NOT GIVEN must not |
| `R-TFNG-003` | must | NOT GIVEN items carry a stated justification of what the passage omits |
| `R-TFNG-004` | should | Key distribution is not degenerate (no answer type > 60 % of the set) |
| `R-TFNG-005` | should | Statement is a claim, not a question |
| `R-TFNG-006` | should | Statement does not merely copy a passage sentence verbatim |

⚠️ True/False/Not Given is the type where local models fail most often, because the False vs. Not
Given distinction requires reasoning about what a text does *not* assert. Rules can enforce structure
here but cannot verify the judgement. **This type carries a permanently higher human-review rate.**

#### Multiple choice

| Code | Severity | Check |
|------|----------|-------|
| `R-MCQ-001` | must | Exactly one option is keyed correct (unless the type is multi-select) |
| `R-MCQ-002` | must | Option count matches the declared type (usually 4) |
| `R-MCQ-003` | must | Options are mutually distinct (rapidfuzz < 0.85 pairwise) |
| `R-MCQ-004` | should | Option lengths are comparable — a conspicuously longest option is a giveaway |
| `R-MCQ-005` | should | No "all/none of the above" |
| `R-MCQ-006` | should | Distractors are drawn from passage vocabulary (plausible), not invented |
| `R-MCQ-007` | should | Correct-answer position is not clustered across the set |
| `R-MCQ-008` | must | No option is a superset/paraphrase of the correct one |

`R-MCQ-004` and `R-MCQ-007` catch the two classic tells of machine-written MCQs: the correct answer
being visibly the most detailed option, and the key drifting toward one letter.

#### Heading matching

| Code | Severity | Check |
|------|----------|-------|
| `R-HEAD-001` | must | Headings ≥ paragraphs (distractors required) |
| `R-HEAD-002` | must | Mapping is one-to-one; no paragraph unassigned or double-assigned |
| `R-HEAD-003` | must | Every paragraph referenced exists |
| `R-HEAD-004` | should | Headings are noun phrases, not sentences |
| `R-HEAD-005` | should | No heading repeats a paragraph's opening words verbatim |

#### Set-level rules

| Code | Severity | Check |
|------|----------|-------|
| `R-SET-001` | must | Item count matches the request |
| `R-SET-002` | must | Question-type mix matches the plan |
| `R-SET-003` | should | Order-dependent types follow passage order |
| `R-SET-004` | should | Difficulty progresses as planned |
| `R-SET-005` | should | Items are spread across the passage, not clustered in early paragraphs |
| `R-SET-006` | must | No two items test the same fact |

`R-SET-005` is worth its weight: generators reliably over-mine the first two paragraphs because
that's what dominates attention early in the context.

---

## L2 — Originality and deduplication

Two distinct checks with very different consequences.

### Against the reference corpus — hard block

```
generated text ──▶ normalise ──▶ 8-gram shingles ──▶ MinHash
                                                        │
                          reference_documents ──────────┤
                                                        ▼
                                          any 8-gram exact match?
                                        ──yes──▶ QUARANTINE + alert
                                                 never publishable
```

An 8-word verbatim overlap with copyrighted material is not a coincidence, it is regurgitation. It is
a hard block with no override and an operator alert, because a single incident of publishing
copyrighted text is a business-ending category of problem, not a quality issue.

This is the **only** permitted use of `reference_documents`. See
[Compliance](11-security-copyright-compliance.md).

### Against our own bank — soft block

```
new item ──▶ embed (nomic-embed-text) ──▶ pgvector cosine search
                                             │
                    similarity > 0.95  ──▶ duplicate, reject
                    0.88 – 0.95        ──▶ flag for reviewer
                    < 0.88             ──▶ accept
```

Thresholds are initial estimates and **must be tuned against real data** once a few thousand items
exist. They are configuration, not constants, and the tuning is a scheduled Phase 2 task.

---

## L3 — The LLM critic

The critic runs **last among machine checks** and only on content that already passed L0–L2.

### Its contract

```python
class CriticFinding(BaseModel):
    category: FindingCategory   # ambiguity | weak_distractor | multiple_defensible_answers
                                # register_mismatch | factual_doubt | cultural_bias
                                # awkward_phrasing | answer_not_supported
    target: str                 # 'item:3' | 'passage:para_C'
    severity: Severity
    explanation: str
    suggested_fix: str | None
    confidence: float           # self-reported; treated as weak evidence only

class CriticOutput(BaseModel):
    findings: list[CriticFinding]
    # NOTE: there is deliberately no overall_score field.
```

**There is no score field, and adding one is a design regression.** The critic's job is to point at
specific things a human should look at. The moment it emits a number, that number will be used to
skip review, and the system's trustworthiness collapses to the reliability of a 9 B model's opinion.

### Isolation requirements

To keep the critic's opinion worth anything:

1. Different model from the generator where memory allows; different prompt and temperature at
   minimum.
2. **No access to the generation rationale, plan, or prior critic findings.** It sees the finished
   artefact exactly as a human reviewer would.
3. It receives the passage and items, and nothing about how they were made.
4. It runs once per revision cycle, never in a self-correcting loop with the generator.

### What the critic is genuinely good at

| Good at | Poor at |
|---------|---------|
| Spotting ambiguous stems | Judging band level accurately |
| Noticing two defensible answers | Consistent numeric scoring |
| Register/tone mismatch | Its own confidence calibration |
| Culturally narrow assumptions | Anything a rule already checks |
| Awkward or unidiomatic phrasing | Reliably finding subtle factual errors |

Never ask the critic to check something a rule can check. It is slower, costs money, and is less
reliable — and a disagreement between the two just creates noise a human has to resolve.

---

## L4 — Human review

The scarcest resource in the system. Design goal: **maximise defects caught per reviewer-minute**,
not maximise items reviewed.

### Sampling policy

Exhaustive review does not scale and is not necessary once the machine layers are calibrated.

| Content profile | Review rate |
|-----------------|-------------|
| New question type, or a prompt version's first 50 items | **100 %** |
| Type with historical approval rate < 80 % | 100 % |
| Any True/False/Not Given item | 100 % (until calibration says otherwise) |
| Type with approval ≥ 90 % over the last 200 items | 25 % random sample |
| Any item with a `should`-level rule failure | 100 % |
| Any item with a critic finding of severity ≥ `should` | 100 % |
| Everything else | 10 % random sample |

Sampling rates are **derived from measured approval rates**, never set by intuition. When a type's
sampled approval rate drops, its rate automatically returns to 100 %.

### Making review fast

- Passage and items side by side; evidence spans highlighted **in the passage**.
- Findings anchored inline to the text they refer to, not listed in a separate panel.
- Keyboard-first: approve, reject, request changes, next — no mouse.
- Rejection requires a `reason_code` from a fixed vocabulary. Comments are optional.
- `time_spent_seconds` recorded automatically to track the reviewer-minutes metric.

Reason codes are the highest-value data the system produces. Six months of coded rejections tells you
exactly which prompt to fix and which rule to write — but only if they aggregate, which free text
does not.

---

## Calibration — how we make quality claims defensible

You have no IELTS examiner on the team. That is the central constraint on this whole document, and
it has a better answer than "trust the model".

### Method 1 — Run the rule engine against authentic IELTS papers ★

**The highest-leverage action available, and it needs zero examiner time.**

```
authentic, published IELTS papers ──▶ rule engine ──▶ any MUST failures?
                                                         │
                                            yes ──▶ OUR RULE IS WRONG
```

A real Cambridge paper is, by definition, valid IELTS content. If our rule engine flags it, the bug is
ours. This gives us a genuine **false-positive rate** for every rule, using material you already have,
with no expert judgement required.

Target: **≤ 5 % false-positive rate** before the rule engine is allowed to block content in anger.

Report: `GET /api/v1/quality/reports/calibration`, run via `make calibrate`.

> This uses authentic material for *structural measurement only*. No passage text enters a prompt.
> See [Compliance](11-security-copyright-compliance.md).

### Method 2 — Distribution matching

Authentic papers also give us reference distributions:

| Feature | Use |
|---------|-----|
| Passage word count | Expected range |
| Flesch-Kincaid by band | Readability target |
| Answer position spread across the passage | Detect front-loading |
| Distractor/key length ratio | Detect the "longest option is correct" tell |
| Question-type mix per paper | Realistic planning |
| Vocabulary frequency profile | CEFR banding |

Generated content that falls outside the authentic distribution is suspicious even when no individual
item is provably wrong. These become `should`-level rules with empirically derived thresholds rather
than guessed ones.

### Method 3 — Planted-defect detection ★

The cheapest real measurement of the critic. Take clean items and deliberately introduce known
defects: paraphrase an answer so it is no longer verbatim, make two MCQ options both defensible,
flip a True to a Not Given, insert a subtle contradiction.

Ground truth is exact because **we planted it**. This yields real precision and recall for the critic
and for every candidate model — with no examiner and no labelling effort.

Lives in `evals/benchmarks/` as Task 5. Runs in CI on every prompt change.

### Method 4 — Team golden set

100–150 items labelled by the team against published IELTS band descriptors and format specs. Not
examiner-grade, but it makes evaluator agreement **measurable** instead of assumed. Label
independently, in duplicate, and record inter-rater agreement — if the team cannot agree with itself,
the model's agreement with the team is meaningless.

### Method 5 — Buy one examiner pass

⚠️ **Still the recommended purchase.** One certified examiner reviewing ~100 items converts methods
1–4 from proxies into validated ground truth. Roughly a day of expert time, and it is the difference
between "our rules pass" and "our content is good". Tracked in
[Open Questions](../execution/open-questions.md).

---

## What we report

The quality reports show **verdicts and rates**, never a synthetic composite score.

```
Reading · last 30 days · prompt v3 · qwen3.5:9b

Generated                      412
Passed schema (L0)             389   94.4 %
Passed all MUST rules (L1)     301   77.4 %
Passed originality (L2)        299   99.3 %
Critic findings ≥ should       142   47.5 %
Submitted to review            299
Approved first pass            214   71.6 %   ← the headline number
Rejected                        41   13.7 %
Changes requested               44   14.7 %

Top MUST failures
  R-COMP-001  answer not verbatim in passage      67
  R-MCQ-001   multiple defensible correct options  31
  R-ITEM-005  evidence quote mismatch              22

Top rejection reasons
  weak_distractor      18
  ambiguous_stem       11
  band_mismatch         7

Rule engine calibration (vs 6 authentic papers)
  False-positive rate  3.1 %   ✅ within target
```

**Approval rate is the headline metric.** It is grounded in human judgement, it is falsifiable, and it
moves when quality genuinely changes. `R-COMP-001` failing 67 times is a specific, actionable signal:
the passage prompt needs to instruct verbatim extraction more forcefully. "Quality: 92/100" would have
told us nothing we could act on.

---

## Evolution

The quality system is expected to keep changing, and that is designed for:

1. **Every reviewer rejection is a candidate rule.** If a human catches something twice, ask whether a
   rule can catch it. Reason-code frequency drives the rule backlog.
2. **Rules are versioned** (`engine_version` on every check) so historical results stay interpretable
   after a rule changes.
3. **Rules are tested against authentic material before activation** — no rule ships without a
   measured false-positive rate.
4. **Prompt changes must pass the golden set** before activation
   (`POST /api/v1/prompts/{name}/versions/{v}/evaluate`). This is enforced in CI.
5. **Thresholds are data-derived.** Every number in this document that is currently an estimate
   (similarity cutoffs, readability ranges, sampling rates) is tagged for tuning once real data
   exists.
