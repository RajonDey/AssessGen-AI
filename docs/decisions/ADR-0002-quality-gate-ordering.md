# ADR-0002 — Deterministic rules before LLM judgement

**Status:** Accepted · **Date:** 2026-07-30

## Context

The original design had an Evaluator Agent returning an overall quality score (e.g. `92/100`), with a
Critic Agent and a revision loop running until a threshold was met.

Three problems make that score untrustworthy:

1. **Self-evaluation bias.** An LLM grading content from a comparable LLM inflates its judgement. The
   reasoning that produced an error also endorses it. On a 9 B local model — our development
   configuration — this is severe.
2. **Unfalsifiability.** With no ground truth, nothing could show that 92 is wrong. A metric that
   cannot be wrong cannot be improved.
3. **Dimensional collapse.** "Answer key is factually wrong" and "distractor is slightly weak" must
   not average into one number. One is a hard block, the other a note for a reviewer.

Separately, a large share of IELTS format requirements are **objectively checkable**: an answer either
appears verbatim in the passage or it does not.

## Decision

Five layers, cheapest and most certain first:

```
L0 schema (Pydantic) → L1 deterministic rules → L2 originality/dedup → L3 LLM critic → L4 human
```

- Deterministic rules produce **verdicts** with severity; `must` failures are absolute blocks with no
  override.
- The LLM critic produces **structured findings only**. `CriticOutput` has no score field, by design.
- Where a rule and the critic disagree, the rule wins.
- The critic must use a different model or, at minimum, a different prompt and temperature, and must
  never see the generation rationale.
- Revision loops are hard-capped at 2. Hitting the cap fails the run loudly with findings attached.

## Alternatives considered

| Option | Why rejected |
|--------|--------------|
| LLM evaluator with a numeric score (original) | Unfalsifiable, biased, dimensionally collapsed |
| LLM critic only, no rules | Discards free, certain signal. Slower, costlier, less reliable for anything a rule can express |
| Rules only, no critic | Rules cannot express ambiguity, register mismatch, or "two defensible answers" |
| Human review of everything | Does not scale. Human time is the scarcest resource in the system |
| Unbounded revision until threshold | With a weak model, may never converge; unbounded cost and latency |

## Consequences

**Positive**
- Most defects are caught for free, deterministically, in milliseconds.
- Rules are unit-testable and their false-positive rate is measurable against authentic material.
- The expensive layers only ever see pre-filtered content.
- A mediocre local model becomes usable, because the rules enforce what it cannot reliably self-impose.
- Quality reporting shows actionable specifics (`R-COMP-001` failed 67×) instead of an opaque number.

**Negative**
- Writing rules is real, ongoing work — roughly 40+ rules for Reading alone.
- Rules can be wrong, and a wrong `must` rule blocks valid content. Mitigated by mandatory calibration
  against authentic papers before a rule may block.
- No override for `must` will occasionally frustrate a reviewer who is right. This is accepted
  deliberately: an override button turns every guarantee into a suggestion within about a month.
- Judgement-heavy modules (Writing, Speaking) benefit less from this design and remain harder.

**Neutral**
- The `quality_checks` table grows quickly — one row per rule per version.

## Reversal criteria

- Calibration shows a false-positive rate persistently above 10 % that rule fixes cannot reduce —
  suggesting our formalisation of IELTS rules is wrong at a deeper level.
- A future model demonstrates, on the planted-defect benchmark, precision and recall above ~95 % on
  defects our rules catch. Then the critic could plausibly take on more load — though rules would
  remain preferable for being free and deterministic.
- Note: "the critic seems good in practice" is **not** reversal evidence. Only planted-defect
  benchmark numbers or examiner-validated agreement count.
