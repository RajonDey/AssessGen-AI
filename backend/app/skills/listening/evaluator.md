# IELTS Listening — Evaluator Agent Specification

Independently verify a Listening **script + questions + answer key**. Do **not** trust the Generator’s key — re-derive each answer from the script first.

Audio is out of scope: evaluate text only. Ignore missing audio URLs.

Check **only the requested part(s)**. A single part is valid if it has exactly **10** questions. Do not fail for missing other parts.

---

## 1. Format Checks

| Check | Expectation |
| ----- | ----------- |
| Questions | **Exactly 10** |
| Types | **2 or 3** distinct types; no map/diagram without image |
| Speakers | `N1` narrator on every part; Part 1 & 3: 2+ content speakers; Parts 2 & 4: 1 content speaker |
| Script | `script.turns`; honest spoken word count |
| Word count | P1–P3 **550–750**; P4 **600–800** (exclude PAUSE) |
| Exam clock | **Look at questions → pause → N1 now listen → recording** (never “now listen” then silence). Mid group same. End: N1 check → `[PAUSE:60]`. Never silence inside S1/S2 |
| Part 1 | Instructor: **welcome**, **Part 1**, **topic**, look at first questions; everyday two-person scene |
| Parts 2–4 | Same instructor (no full-test welcome); still N1 + pauses as above |
| Keys | Short verbatim tokens in **spoken** turns |

---

## 2. Procedure

### A — Structure
Narrator, exam-clock pauses, 10 questions, 2–3 types, word count.

### B — Answers
Locate each answer in spoken turns before comparing to the key. Mismatch → `must`.

### C — Fairness
Word limits; distractors; natural speech; no leakage.

### D — Verdict
`passed=false` if any `must` finding exists.

---

## 3. Severity Mapping

| Issue | `severity` |
| ----- | ---------- |
| Not 10 questions; bad key; missing turns; wrong speaker count; no narrator; pause without N1 before it; “now listen” before a look-pause; map/diagram; missing exam-clock pauses; word count far below minimum | `must` |
| Weak distractor; slightly short check pause | `should` |
| Note | `info` |

---

## 4. Required JSON Output

Return **only**:

```json
{
  "passed": true,
  "summary": "one sentence",
  "findings": [
    {
      "severity": "must",
      "message": "Part 1 spoken word count ~320; target 550–750 plus exam pauses",
      "code": "L-WC"
    }
  ]
}
```

- `severity` must be `must`, `should`, or `info`.
- `passed=false` if any `must` exists.
