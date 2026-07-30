# Module — Speaking

## The honest framing

Speaking is the **least machine-checkable** module and, for that reason, is scheduled last.

Almost nothing in it can be verified deterministically. There is no passage to match answers against,
no chart data to check claims against, no verbatim key. The valuable output — band-differentiated
sample responses — is exactly the part we cannot validate without an examiner.

But it is also the module where the generation task is genuinely easy. Speaking questions are short,
formulaic and highly patterned. A small local model produces usable Part 1 questions and Part 2 cue
cards with little difficulty.

So the strategy is: **generate questions confidently, generate sample answers cautiously, and label
band claims honestly.**

---

## Format specification

| Part | Content | Duration |
|------|---------|----------|
| 1 | Introduction and interview on familiar topics | 4–5 min |
| 2 | Long turn from a cue card — 1 min preparation, 1–2 min speaking | 3–4 min |
| 3 | Two-way discussion of abstract issues linked to Part 2 | 4–5 min |

Total 11–14 minutes, one-to-one with an examiner.

### Part 1
Three familiar topics (home, work, study, hobbies, food, weather), roughly four questions each. Short
personal questions with straightforward answers.

### Part 2 — the cue card

```
Describe a skill you learned that was difficult.

You should say:
  what the skill was
  when and why you learned it
  how you learned it

and explain why you found it difficult.
```

Structure is rigid: a topic line, three "you should say" bullets, and a final "and explain…" prompt.
That rigidity makes it unusually machine-checkable for this module.

### Part 3
Abstract, analytical questions thematically linked to Part 2, escalating in difficulty — typically
opinion, comparison, speculation about the future, and evaluation of causes or consequences.

**The Part 2 → Part 3 thematic link is the defining structural property of the module and the thing
generators most often get wrong.** Part 3 must interrogate the *abstract domain* the Part 2 topic
belongs to (learning, skill acquisition, education) rather than repeat the personal question.

---

## Pipeline

```
request { topic_domain, target_band }
    │
    ▼
TOPIC PLANNER          choose a Part 1 topic set + a Part 2 theme + its abstract domain
    │
    ▼
PART 1 GENERATOR       3 topics × 4 questions
PART 2 GENERATOR       cue card: topic + 3 bullets + explain prompt
PART 3 GENERATOR       5–6 abstract questions in the Part 2 domain
    │
    ▼
QUALITY L0-L2
  R-SPK-001..010 · originality · dedup
    │
    ▼
SAMPLE ANSWER GENERATOR   per part, per target band (6, 7, 8, 9)
    │
    ▼
BAND JUSTIFICATION        per official criterion, with evidence quoted
    │
    ▼
QUALITY on answers        duration estimate · criterion coverage · monotonicity
    │
    ▼
CRITIC ──▶ REVISER (bounded)
    │
    ▼
HUMAN REVIEW ──▶ approved
    │
    ▼
(optional, later) TTS      spoken sample answers via Kokoro
```

---

## Quality rules

Despite the module's judgement-heavy nature, its rigid structure yields more checkable rules than one
might expect.

### Structural

| Code | Severity | Check |
|------|----------|-------|
| `R-SPK-001` | must | Part 2 cue card has exactly three "you should say" bullets |
| `R-SPK-002` | must | Part 2 ends with an "and explain…" prompt |
| `R-SPK-003` | must | Part 1 has 3 topics with 3–4 questions each |
| `R-SPK-004` | must | Part 3 has 4–6 questions |
| `R-SPK-005` | must | Part 2 bullets are answerable independently and are not redundant |

### Content

| Code | Severity | Check |
|------|----------|-------|
| `R-SPK-006` | **must** | **Part 3 questions are thematically linked to the Part 2 topic** |
| `R-SPK-007` | must | Part 3 questions are abstract, not personal ("Why do people…", not "Do you…") |
| `R-SPK-008` | should | Part 1 questions are answerable in 20–30 seconds |
| `R-SPK-009` | should | Part 2 topic is accessible regardless of culture, wealth or geography |
| `R-SPK-010` | should | No question presumes a specific life circumstance (car ownership, foreign travel, siblings) |
| `R-SPK-011` | should | Part 3 difficulty escalates across the sequence |

`R-SPK-006` is checkable with embedding similarity between the Part 2 topic and each Part 3 question:
too low means the link is broken; **too high means Part 3 is merely repeating Part 2 rather than
abstracting from it.** Both ends of that range are failures, which makes it a genuinely two-sided
check rather than a threshold.

`R-SPK-009` and `-010` matter more here than anywhere else in the system. "Describe a car journey you
enjoyed" is unanswerable for a candidate who has never owned a car, and a model trained largely on
affluent-Western text produces such prompts readily and without any signal that it has done so.

---

## Sample answers

### The same honesty problem as Writing

⚠️ We cannot verify that a "Band 8 sample answer" is Band 8. The public Speaking criteria are:

| Criterion | Weight |
|-----------|--------|
| Fluency and Coherence | 25 % |
| Lexical Resource | 25 % |
| Grammatical Range and Accuracy | 25 % |
| Pronunciation | 25 % |

**Pronunciation cannot be represented in text at all.** A text sample answer can only ever address
three of the four criteria, and any band label derived from text alone is therefore structurally
incomplete. This must be stated in the product, not buried.

### What is checkable

| Code | Severity | Check |
|------|----------|-------|
| `R-SANS-001` | must | Part 2 answer length implies 1–2 minutes at natural speech rate (~140 wpm) |
| `R-SANS-002` | must | Part 2 answer addresses all three bullets plus the explain prompt |
| `R-SANS-003` | must | Justification quotes appear verbatim in the answer |
| `R-SANS-004` | should | Lexical diversity increases monotonically across bands |
| `R-SANS-005` | should | Discourse-marker range increases across bands |
| `R-SANS-006` | should | Answers read as spoken language, not written prose |
| `R-SANS-007` | must | Band labels state that pronunciation is not assessed in text |

`R-SANS-006` is the most commonly violated in practice. LLMs write essays when asked for speech. A
genuine Band 7 spoken answer contains false starts, self-correction, fillers and looser syntax than
any model produces by default. Countering it needs an explicit prompt instruction plus a checkable
signal — contraction rate, filler presence and mean clause length are reasonable proxies.

### Labelling policy

Same as Writing: **"estimated band"** with an explanatory note, plus an explicit statement that
pronunciation is not assessed. Converting to validated labels requires the examiner pass tracked in
[Open Questions](../execution/open-questions.md).

---

## Optional: spoken sample answers

Once Kokoro is in place for Listening, sample answers can be synthesised.

⚠️ **A significant caveat.** TTS produces fluent, well-paced, error-free speech. That is close to a
Band 9 delivery regardless of the text being spoken. A "Band 6 sample answer" rendered in flawless TTS
is actively misleading — the delivery contradicts the label, and delivery is what a learner will
imitate.

Options, in order of preference:

1. **Synthesise Band 8–9 answers only**, where fluent delivery is consistent with the label.
2. Synthesise all bands with a prominent note that delivery does not reflect the band.
3. Do not synthesise sample answers at all; use TTS only for examiner questions.

**Recommendation: option 1, plus TTS for the examiner questions in all parts.** Spoken examiner
questions are unambiguously useful — they let a learner practise under realistic conditions — and
carry none of this problem.

---

## Definition of done

- [ ] Parts 1–3 generating with correct structure and verified thematic linkage
- [ ] `R-SPK-*` implemented and unit tested, including the two-sided linkage check
- [ ] Cultural-accessibility rules implemented and spot-checked against real output
- [ ] Sample answers at Bands 6–9 with evidenced justifications
- [ ] Monotonicity checks passing
- [ ] Band-labelling policy, including the pronunciation caveat, visible in the UI
- [ ] A complete Speaking test (Parts 1–3) assembled and published

## Phasing

| Phase | Scope |
|-------|-------|
| 1 | Part 1 and Part 2 cue-card generation with review. Structurally checkable, immediately useful |
| 2 | Part 3 with thematic linkage checks; sample answers with band justification |
| 3+ | TTS for examiner questions; Band 8–9 spoken samples |
| Later | Examiner validation → validated band labels |
