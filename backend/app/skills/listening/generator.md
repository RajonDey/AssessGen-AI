# IELTS Listening — Generator Agent Specification

You produce a **TTS-ready Listening script** + question set + answer key. Audio synthesis comes later; the script must be speakable as-is (speaker-labeled turns). An Evaluator verifies your output independently — self-check rigorously before submitting.

**Phase scope:** text only (script + questions). Do not invent audio URLs.

Do **not** copy authentic exam recordings. Invent original situations. Practice material *for* IELTS — no official affiliation claims.

---

## 1. Official Test Format

| Element | Detail |
| ------- | ------ |
| Total parts | 4 (you may generate 1–N parts per request) |
| Questions | **Exactly 10 per part** |
| Types per part | **2 or 3** different types (separate `questionGroups`) |
| Typical split | **6 + 4** (like Q1–6 then Q7–10) or **5 + 5** |
| Recording | Heard once only |
| Accents | british, american, australian, new_zealand |

### Part-by-part content

| Part | Speakers (plus narrator `N1`) | Context |
| ---- | ----------------------------- | ------- |
| **1** | 2 conversation | Everyday social (booking, first day at work, enquiry) |
| **2** | 1 monologue | Everyday social (local facilities / guided talk) |
| **3** | 2–4 discussion | Educational / training |
| **4** | 1 monologue | Academic lecture |

When the request is a **single part**, produce **only that part** (Part 1 → Q1–10, Part 2 → Q11–20, Part 3 → Q21–30, Part 4 → Q31–40).

### Exam-clock duration (WAV length ~6–8 minutes)

Total file length comes from **speech + silences**, not 7 minutes of nonstop talk.

Practice pacing ~130–150 wpm. **Spoken words exclude pause tags.**

| Part | Spoken words | Speech (approx.) | Silences (TTS `[PAUSE:N]`) | Target WAV |
| ---- | ------------ | ---------------- | -------------------------- | ---------- |
| **1–3** | **550–750** | ~4–5 min | look 1 (~40s) + look 2 (~25s) + check (~60s) | **~6–8 min** |
| **4** | **600–800** | ~4.5–5.5 min | same pause pattern | **~7–8 min** |

Do **not** submit a ~300-word stub. Do **not** write 1000+ words of continuous speech with no pauses.

---

## 2. Allowed Question Types

Prefer: multiple choice (A/B/C), matching, form/note/table/flow-chart/summary completion, sentence completion, short-answer.

**Do not use** plan/map/diagram labelling unless an image asset is provided.

### Mandatory layout

- Exactly **10** question objects.
- **Two** groups preferred (6+4 or 5+5); 3 groups allowed if types stay 2–3.
- Short keys (words/numbers/letters), verbatim in **spoken** turns.
- Dense facts: names (spell them), phone numbers, floors, times, “no that’s not your job…”.
- At least one distractor per group (wrong guess, then the real rule).

---

## 3. Word-Limit / Gap-Fill Rules

- Explicit word limit on gap-fill / short-answer.
- Answers usable **exactly as spoken**; no contractions as keys.
- Spell out names/codes/numbers that could be misheard.

---

## 4. Exam-clock script (all parts 1–4)

Every part uses narrator `N1` (`role: narrator`) plus the content speakers. TTS inserts **silence** from `PAUSE` turns — never describe pauses in prose.

Pause text must be `[PAUSE:40]`, `[PAUSE:30]`, `[PAUSE:25]`, or `[PAUSE:60]` (integer seconds).

### Required N1 instructor lines (same person on every part)

N1 is the **exam instructor**, not a character. S1/S2 never give test rules. **Look at questions → silence → then “now listen” → conversation.** Do not say “now listen” before the look-at-questions pause.

1. **Opening:** Part 1 includes the full **welcome** (practice test; recordings **once only**; **four parts**). Every part: **which part**, **topic** (“you will hear…”), **look at / review** the first question group — then `[PAUSE:40]`. Then N1: “Now listen and answer …” — then content.
2. **Mid:** look at / review the **second** group — then `[PAUSE:25]`. Then N1: “Now listen …” — then the same scene continues. Do not pause inside S1/S2.
3. **Close:** end of this part; **one minute to check** — then `[PAUSE:60]`. Nothing after that pause.

Do not give N1 the same gender+accent as a conversation speaker.

### Required turn order

1. **`N1`** — frame this part (Part 1 also includes the **full practice-test welcome** once; Parts 2–4 do **not** repeat the welcome).
   - Say what they will hear (conversation / talk / discussion / lecture).
   - “First, you have some time to look at questions {first group}.” (Do **not** say “now listen” yet.)
2. **`PAUSE` `[PAUSE:40]`** (30 is acceptable) — time to read the first group.
3. **`N1`** — “Now listen carefully and answer questions {first group}.”
4. **Content** — first half of the **same** recording (answers for the first group).
5. **`N1`** — “Before you hear the rest, you have some time to look at questions {second group}.”
6. **`PAUSE` `[PAUSE:25]`** (20–30 OK).
7. **`N1`** — “Now listen and answer questions {second group}.”
8. **Content continues** — second half of the **same** situation.
9. **`N1`** — “That is the end of Part {N}. You now have one minute to check your answers to Part {N}.”
10. **`PAUSE` `[PAUSE:60]`** — check time.

Part **1** welcome (paraphrase OK): welcome to this IELTS-style Listening **practice** test; recordings once only; time to read and check; four parts; now look at Part 1 — then the look-at-questions line and `[PAUSE:40]`.

---

## 5. Required Output

**JSON is required** (not optional Markdown). Include `N1` in `speakers[]`. Example **shape** (abbreviated — your script must hit the word-count table and all 10 questions):

```json
{
  "type": "listening",
  "partNumber": 1,
  "context": "short situation",
  "speakers": [
    {"id": "N1", "role": "narrator", "gender": "female", "accent": "british"},
    {"id": "S1", "role": "supervisor", "gender": "male", "accent": "british"},
    {"id": "S2", "role": "new worker", "gender": "female", "accent": "british"}
  ],
  "script": {
    "turns": [
      {"speaker": "N1", "text": "Welcome to this IELTS-style Listening practice test. … Now look at Part 1. You will hear two people talking. First, you have some time to look at questions 1 to 6."},
      {"speaker": "PAUSE", "text": "[PAUSE:40]"},
      {"speaker": "N1", "text": "Now listen carefully and answer questions 1 to 6."},
      {"speaker": "S1", "text": "… first-half dialogue with spellings, numbers, distractors …"},
      {"speaker": "N1", "text": "Before you hear the rest of the conversation, you have some time to look at questions 7 to 10."},
      {"speaker": "PAUSE", "text": "[PAUSE:25]"},
      {"speaker": "N1", "text": "Now listen and answer questions 7 to 10."},
      {"speaker": "S1", "text": "… second-half dialogue, same situation …"},
      {"speaker": "N1", "text": "That is the end of Part 1. You now have one minute to check your answers to Part 1."},
      {"speaker": "PAUSE", "text": "[PAUSE:60]"}
    ]
  },
  "word_count": 620,
  "parts": [{"partNumber": 1, "questionGroups": []}],
  "answer_key": {},
  "answer_evidence": {}
}
```

Fill `questionGroups` with **10** questions, `answer_key` / `answer_evidence` for all 10. Count `word_count` honestly (spoken turns only).

---

## 6. Generation Rules

- Build the key **with** the questions; answers in script order.
- Multi-part runs: only this part; harder / different mix than prior parts.
- Unambiguous items only.

---

## 7. Revision Behavior

- Expand a short script; do not only patch labels.
- Re-declare `answer_evidence` and `word_count` after edits.
