# Module — Reading

> **Reading is the reference implementation.** It is built first and built properly. The other three
> modules copy its structure: the rule-engine pattern, the graph shape, the prompt layout, the review
> UI. Effort spent here is amortised three times over — so resist shipping a shortcut.

## Why Reading is the right module to perfect first

It has the highest ratio of **machine-checkable** to **judgement-dependent** correctness of any IELTS
module. An answer either appears verbatim in the passage or it does not. A heading mapping is either
one-to-one or it is not. That means a mediocre local model plus a strict rule engine can produce
genuinely usable output — which is not true for Writing or Speaking, where quality is almost entirely
a matter of judgement we currently cannot verify.

---

## Format specification

### Academic Reading

| Property | Value |
|----------|-------|
| Passages | 3 |
| Total questions | 40 |
| Duration | 60 minutes (no extra transfer time) |
| Passage length | Passage 1 ~800–900; Passage 2 ~850–950; Passage 3 ~900–1050 (~2150–2750 total) |
| Difficulty progression | Passage 1 easiest → Passage 3 hardest |
| Source style | Books, journals, magazines, newspapers — expository/analytical/argumentative |
| Questions per passage | 13–14 |

### General Training Reading

| Section | Content | Questions |
|---------|---------|-----------|
| 1 | Two or three short factual texts (notices, ads, timetables) | ~14 |
| 2 | Two work-related texts (job descriptions, contracts, training) | ~13 |
| 3 | One longer general-interest text | ~13 |

Academic is implemented first; General Training reuses the same graph with a different `spec.py` and
a subset of the rules.

### Question types

Implementation order is deliberate — **most machine-checkable first**. This is not an arbitrary
sequence; it is what lets us build trust in the pipeline before tackling the types where our current
model is weakest.

| # | Type | `item_type` | Machine-checkable | Local model quality |
|---|------|-------------|-------------------|---------------------|
| 1 | Sentence completion | `sentence_completion` | ★★★ verbatim answer | Good |
| 2 | Summary completion | `summary_completion` | ★★★ verbatim answer | Good |
| 3 | Short answer | `short_answer` | ★★★ verbatim answer | Good |
| 4 | Note/table/flowchart completion | `note_completion` | ★★★ verbatim answer | Good |
| 5 | Matching headings | `heading_match` | ★★★ structural bijection | Moderate |
| 6 | Matching information to paragraphs | `info_match` | ★★☆ | Moderate |
| 7 | Matching features | `feature_match` | ★★☆ | Moderate |
| 8 | Multiple choice (single) | `mcq_single` | ★★☆ structure only | **Weak** — distractors |
| 9 | Multiple choice (multi) | `mcq_multi` | ★★☆ | Weak |
| 10 | Diagram labelling | `diagram_label` | ★★☆ needs an image | Weak |
| 11 | True / False / Not Given | `true_false_notgiven` | ★☆☆ structure only | **Weakest** |
| 12 | Yes / No / Not Given | `yes_no_notgiven` | ★☆☆ | **Weakest** |

**Phase 1 target:** types 1–5. **Phase 2:** 6–9. **Phase 3:** 10–12.

⚠️ True/False/Not Given is scheduled last despite being the most recognisable IELTS type. The
False vs. Not Given distinction requires reasoning about what a text *does not assert* — a negative
claim over an open world. Small models fail this frequently and confidently. Rules can enforce its
structure but cannot verify the judgement, so it will carry a permanent 100 % human review rate until
calibration data proves otherwise.

---

## Pipeline

```
request { band, topics[3], type_plan[3], passage_count, question_count, types }
    # see docs/modules/paper-spec.md — independent topics; interlocking types
    │
    ▼
PLANNER ──────────────────────────────────────────────────────
  Allocate: passages × difficulty × topic angle
            question types × counts per passage
            answer-position targets (force spread across paragraphs)
    │
    ├─▶ validate plan against R-SET-* ── invalid ──▶ replan (max 2)
    ▼
PASSAGE GENERATOR  (per passage, sequential — one model lease)
  Produce title + labelled paragraphs (A, B, C…) with char offsets
    │
    ▼
QUALITY L0-L2 on passage
  R-PASS-001..009 · originality 8-gram · dedup embedding
    │  MUST fail ──▶ regenerate (max 2) ──▶ fail run
    ▼
QUESTION GENERATOR  (per type, batched — one call per type per passage)
  Input: passage + target paragraphs + type spec + count
    │
    ▼
ANSWER GENERATOR
  Per item: answer_key + evidence{paragraph, start, end, quote} + explanation
    │                              ▲
    │                              └── mandatory; this is what makes L1 possible
    ▼
QUALITY L0-L2 on items
  R-ITEM-* · R-COMP-* · R-MCQ-* · R-HEAD-* · R-TFNG-* · R-SET-*
    │  MUST fail ──▶ REVISER (targeted, max 2 loops)
    ▼
CRITIC  (different model/prompt; sees only the finished artefact)
  Structured findings: ambiguity, weak distractors, multiple defensible answers
    │  blocking findings ──▶ REVISER
    ▼
PERSIST  passage_version + item_versions + quality_checks + embeddings
    ▼
interrupt()  ──▶ human review ──▶ resume ──▶ approved
```

**Batching by question type, not per item.** One call producing six sentence-completion items is both
cheaper and better than six calls: the model can see the set and avoid testing the same fact twice,
which directly serves `R-SET-006`.

---

## Prompt design

### Passage generation

The prompt must carry, explicitly:

- Target band and its **concrete** implications — sentence length range, vocabulary frequency band,
  clause complexity. "Write at Band 7" alone is not actionable for a small model.
- Topic and a specific angle, to avoid the generic encyclopedia-entry register.
- Word count with a tolerance.
- **Paragraph labelling requirement** (A, B, C…) — structural, so downstream offsets work.
- An explicit originality instruction: write from general knowledge, do not reproduce any specific
  published text.
- Genre: expository / argumentative / descriptive.
- A requirement for **factual density** — a passage needs enough discrete, checkable facts to support
  13 questions. This is the most common cause of a passage that generates poor questions.

**Not in the prompt:** any authentic IELTS passage as an example. See
[Compliance](../core/11-security-copyright-compliance.md).

Known failure modes to counter explicitly in the prompt:

| Failure | Counter |
|---------|---------|
| Front-loading all facts in paragraphs A–B | Require even distribution; `R-SET-005` checks it |
| Uniform sentence length (machine cadence) | Require varied structure; `R-PASS-006` checks it |
| Vague, unquestionable prose | Require named entities, dates, figures, contrasts |
| Meta-commentary ("In this passage we explore…") | Explicit prohibition; `R-PASS-003` checks it |
| Sliding to encyclopedic register | Specify genre and intended publication |

### Question generation

Type-specific prompts, each with its own Pydantic output schema. Every prompt carries the
corresponding rules as **generation constraints** — telling the model up front what will be checked is
much cheaper than discovering violations afterwards and revising.

Example for completion types:

```
CONSTRAINTS (these will be automatically verified):
- The answer MUST appear word-for-word in the passage. Do not paraphrase.
- The answer MUST be at most {word_limit} words.
- Return the exact character offsets where the answer appears.
- The answer MUST NOT be a function word (a, the, of, and, in).
- The sentence MUST remain grammatical when the gap is filled.
```

This shifts a large share of `R-COMP-001` failures from post-hoc rejection into prevention — the
single most effective prompt technique available for this module.

---

## Answer key format

```json
{
  "type": "exact",
  "values": ["photosynthesis"],
  "accept": ["the photosynthesis process"],
  "case_sensitive": false
}
```

| Key type | Used by |
|----------|---------|
| `exact` | Completion, short answer |
| `choice` | MCQ — option keys |
| `enum` | True/False/Not Given, Yes/No/Not Given |
| `mapping` | Heading match, feature match — `{"A": "vi", "B": "iii"}` |
| `set` | Multi-select MCQ — order-independent |

`accept` holds legitimate alternates so IELTS Ready can grade by exact comparison rather than fuzzy
matching at test time. Deciding what is acceptable is a content decision made once, at authoring time,
by a reviewer — not a runtime heuristic applied to every student.

## Evidence format

```json
{
  "paragraph": "C",
  "start": 1204,
  "end": 1279,
  "quote": "Plants convert sunlight into chemical energy through photosynthesis."
}
```

Offsets are absolute into `passage_versions.body`. `R-ITEM-005` verifies `body[start:end] == quote`.
This turns "is the answer right?" from a model judgement into a string comparison — and it is the
mechanism the whole module's trustworthiness rests on.

---

## Module-specific rules

The full catalogue is in [Quality & Evaluation](../core/08-quality-and-evaluation.md). The rules that
matter most in practice:

| Rule | Why it earns its place |
|------|------------------------|
| `R-COMP-001` | Verbatim answer check. Catches the single most common and most damaging failure |
| `R-ITEM-005` | Evidence quote matches passage at offsets. Catches hallucinated evidence |
| `R-MCQ-001` | Exactly one defensible answer. Catches the most common MCQ defect |
| `R-SET-005` | Answer spread across paragraphs. Catches front-loading |
| `R-MCQ-004` | Comparable option lengths. Catches "longest option is correct" |
| `R-TFNG-004` | Non-degenerate key distribution. Catches all-TRUE sets |

---

## Difficulty and band calibration

Band targeting is genuinely hard and we should be honest that our first version will be approximate.

Signals we can measure deterministically:

| Signal | Source | Direction |
|--------|--------|-----------|
| Flesch-Kincaid grade | `textstat` | Higher → harder |
| Vocabulary frequency profile | `wordfreq` | Rarer → harder |
| Mean sentence length & clause depth | `spaCy` | Higher → harder |
| Answer-to-question lexical overlap | computed | Lower overlap → harder (paraphrase distance) |
| Evidence dispersion | offsets | Spread across paragraphs → harder |
| Distractor–key similarity | embeddings | Closer → harder |

**Answer-to-question lexical overlap deserves emphasis.** It is the closest deterministic proxy for
real IELTS difficulty: easy items let a candidate keyword-match the stem to the passage; hard items
require recognising a paraphrase. It is computable and it is a `should`-level rule.

Initial band mapping is derived from **distribution matching against authentic papers**
(Method 2 in the quality doc), not invented. Until that calibration exists, `target_band` is recorded
as an intent and clearly labelled as unvalidated in the UI.

---

## Current helpers

After generation, `app.content.reading_normalize` aligns `sections[]` with `answer_key`. `app.content.reading_numbering` keeps Academic items continuous: passage 1 is questions 1–13, passage 2 is 14–26, passage 3 is 27–40. Admin downloads (PDF for candidates, Markdown including briefs) are described in [Paper spec](paper-spec.md).

## Definition of done

- [ ] Types 1–5 generating end-to-end with a full quality gate
- [ ] All `R-PASS-*`, `R-ITEM-*`, `R-COMP-*`, `R-HEAD-*`, `R-SET-*` rules implemented and unit tested
- [ ] Rule engine calibrated against ≥ 3 authentic papers, false positives ≤ 5 %
- [ ] Human review UI: passage + items side by side, evidence spans highlighted, keyboard-first
- [ ] Approval rate measured over ≥ 100 reviewed items
- [ ] A complete 3-passage / 40-question Academic test assembled and published
- [ ] Export to PDF and JSON verified
