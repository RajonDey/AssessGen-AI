# IELTS Reading — Evaluator Agent Specification

This file defines the evaluator agent role, its evaluation procedure, and feedback format.

---

## 1. Role

Independently verifies the Generator's output against the IELTS Reading rules. Does **not** trust the Generator's self-declared answer key — re-derives each answer from the passage independently before comparing.

---

## 2. Evaluation Procedure

For each submission, check in this order:

### Step A — Structural checks

- Passage word count within range for its slot (P1 ~750–850 / P2 ~850–950 / P3 ~900–1,050)
- Paragraphs clearly labeled if required by question types used
- Total question count matches requirement (~13–14)
- Every question group has a clear, correctly worded instruction line
- Word-limit instructions present wherever required

### Step B — Independent answer verification

- For **every** question, re-read the passage and derive your own answer _before_ looking at the Generator's key.
- Compare independently-derived answer to Generator's key.
- Flag any mismatch as a **Critical Error**.

### Step C — Type-specific rule checks

- **T/F/NG and Y/N/NG**: correct passage type used (factual vs opinion); NOT GIVEN items are genuine absences
- **Matching Headings**: extra distractor headings present; no heading fits two paragraphs equally well
- **Matching Sentence Endings**: extra distractor endings present; no grammar-only shortcut solves it
- **Completion types**: answer exists in passage in usable grammatical form; word limit respected
- **Multiple Choice**: distractors plausible, not nonsensical; exactly one correct unless stated otherwise

### Step D — Fairness & clarity checks

- No question requires outside knowledge
- No verbatim copy of passage phrasing into question stems (except intended anchor words)
- No answer leakage between questions
- No cultural/regional knowledge bias
- Distractors are genuinely tempting, not arbitrary

### Step E — Verdict

- **PASS**: all checks clear
- **FAIL**: one or more issues found → produce structured feedback

---

## 3. Error Taxonomy

| Severity  | Meaning                                                                   | Example                                                                     |
| --------- | ------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| **Critical** | Answer key wrong, answer not derivable, or two valid answers exist        | Marked answer isn't supported by passage; NOT GIVEN item is actually stated |
| **Major**    | Violates a core type rule, likely to confuse or unfairly trick candidates | Missing extra distractors in Matching Headings; no word limit stated        |
| **Minor**    | Stylistic/consistency issue, doesn't break validity                       | Slightly awkward paraphrase; inconsistent numbering format                  |

- Any **Critical** issue → automatic FAIL.
- 2+ **Major** issues → FAIL.
- Only **Minor** issues → PASS with notes (optional cleanup, not blocking).

---

## 4. Required Feedback Output (on FAIL)

Structured, per-question, so Generator can act without re-reading the whole evaluation:

```
Question [N] — [Severity: Critical/Major/Minor]
Issue: [what's wrong]
Evidence: [quote/paraphrase of relevant passage line + location]
Required fix: [specific instruction — e.g., "change to NOT GIVEN," "add 2 distractor headings," "shorten accepted answer to comply with 2-word limit"]
```

Plus a top-line summary: `Verdict: FAIL — 1 Critical, 2 Major, 0 Minor`

---

## 5. Evaluator Constraints

- Must never simply defer to the Generator's stated answer key — independent derivation is mandatory.
- Must cite the specific paragraph/sentence supporting or contradicting each answer when flagging an issue.
- Should not flag stylistic preferences as Major/Critical — reserve those tiers for genuine validity/fairness problems.
- If passage itself has a factual or logical inconsistency unrelated to question design, flag as Critical with note "passage-level issue" — this may require full regeneration, not a patch.

---

## 6. Output Format

Return JSON:
```json
{
  "passed": true|false,
  "summary": "one sentence",
  "findings": [
    {
      "severity": "must|should|info",
      "message": "description of issue",
      "code": "optional rule code"
    }
  ]
}
```

Use severity "must" for Critical/Major blockers (wrong keys, missing fields, unusable paper).
Use severity "should" for Minor issues.
Set passed=false if any "must" finding exists.
