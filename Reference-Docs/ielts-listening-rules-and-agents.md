# IELTS Listening Module — Question Creation Reference

Companion to the Reading rulebook. This is the shared source-of-truth doc — both agents' standalone system prompts (`listening-generator-prompt.md`, `listening-evaluator-prompt.md`) are built from this content plus their own role-specific sections. If you only need one agent's prompt, use those files directly; use this one for the full picture or to regenerate the split prompts later.

Source: official IELTS.org format pages (jointly owned by British Council, IDP, and Cambridge University Press & Assessment), current as of August 2026, plus commonly-cited practice-test timing norms (clearly marked as such below).

> **Note on "2026 changes":** Some prep-website articles claim new 2026 Listening changes (more global accents, unpredictable part/task order). These are **not confirmed on the official IELTS.org format page** — treat as unverified, not design targets.

---

## 1. Overall Test Structure (Official, Confirmed)

| Element | Detail |
|---|---|
| Total parts | 4 |
| Total questions | 40 (10 per part) |
| Total time | ~30 minutes listening + 10 minutes transfer time |
| Question order | Matches the order of information in the recording |
| Recording | Heard **once only** |
| Accents (officially confirmed) | British, Australian, New Zealand, North American |
| Marking | 1 mark per correct answer; incorrect spelling/grammar loses the mark |

### Part-by-part content

| Part | Speakers | Context | Example |
|---|---|---|---|
| **1** | 2 speakers (conversation) | Everyday, social situation | Booking travel, arranging accommodation |
| **2** | 1 speaker (monologue) | Everyday, social situation | Talk about local facilities/services |
| **3** | 2+ speakers (conversation/discussion) | Educational/training situation | Students discussing an assignment, possibly with a tutor |
| **4** | 1 speaker (monologue) | Educational/training situation | Academic lecture on a subject |

Difficulty increases progressively from Part 1 → Part 4. Questions within each part are answered strictly in the order the information appears in the audio.

### Per-part duration & word-count targets (practice-norm estimate, not official IELTS.org figures)

| Part | Target audio length | Target script word count (~130–150 wpm) |
|---|---|---|
| **1** | 2–3 min | ~300–450 words |
| **2** | 3–4 min | ~400–550 words |
| **3** | 3–4 min | ~400–550 words |
| **4** | ~5 min | ~550–700 words |

Total script: roughly **1,650–2,250 words**, producing **~13–16 minutes of spoken audio** across all 4 parts (excluding pause time). This is shorter than the ~30-minute full exam experience because the real exam also includes instruction read-outs and think-time pauses between question groups, represented here as explicit pause tags (Section 4) rather than spoken content.

---

## 2. Question Types (Official — 6 Types)

### 2.1 Multiple Choice
One question/stem with **3 options (A/B/C)**, choose one; or a longer list where more than one must be chosen (instructions specify the count). Tests detailed and/or general understanding.

### 2.2 Matching
Match a list of items from the recording to a list of options on the paper. Tests detailed listening and how facts relate to each other.

### 2.3 Plan/Map/Diagram Labelling
Complete labels on a visual (diagram, pictures, plan, map) — either select from a given list (write the letter) or take words directly from the recording within a word limit. Tests understanding of spatial description and directions.

### 2.4 Form/Note/Table/Flow-Chart/Summary Completion
Fill gaps in an outline of the recording — Form (facts like names/numbers/addresses), Notes (summarized relationships), Table (categorized info), or Flow Chart (process stages). Same two answer modes as Labelling.

### 2.5 Sentence Completion
Fill a gap in a sentence summarizing key info, within a word limit. Tests identifying important information and relationships (e.g. cause/effect).

### 2.6 Short-Answer Questions
Write a short answer (sometimes 2–3 answers) to a question, within a word limit. Tests listening for concrete facts.

---

## 3. Universal Rules for Word-Limit / Gap-Fill Types

Applies to Labelling, Completion, Sentence Completion, and Short-Answer whenever the answer comes from the recording:

- **Always state an explicit word limit** (e.g. "NO MORE THAN TWO WORDS AND/OR A NUMBER," "ONE WORD ONLY").
- Exceeding the limit loses the mark even if content is correct.
- Words must be usable **exactly as spoken** — never require a word-form change.
- **Never use a contracted word** (e.g. "they're") as a required answer.
- **Hyphenated words count as one word** (e.g. "check-in").
- Numbers, dates, prices, proper nouns are fair content but must be stated unambiguously.

---

## 4. Script Design Rules, Including Required TTS Tags

- Register matches the part: Parts 1–2 = natural everyday/social spoken English; Parts 3–4 = more formal educational/academic spoken English.
- Write **natural spoken dialogue/monologue**, not prose read aloud — realistic hesitations, self-correction, natural turn-taking.
- Each answer must appear **once, clearly, in order** — matching question numbering sequence.
- **In-audio distractors are expected**: a speaker may consider/reject an option before the real answer (e.g. "It used to be on Tuesday, but actually now it's Thursday") — tests careful listening, not keyword-spotting. The *final* stated answer must never be ambiguous.
- No outside/specialist knowledge required.
- Any name/code/number that could be misheard should be **spelled out or repeated** in the script.

### 4.1 Required Tags (machine-parseable, TTS-actionable)

These are not optional and must not be paraphrased into prose — the downstream TTS pipeline (e.g. Kokoro) parses them programmatically:

- **`[PART:N]`** — marks the start of each part (N = 1–4), on its own line. Used to split the script into 4 separate audio-generation segments.
- **`[PAUSE:seconds]`** — marks a silence-insertion point, with an explicit integer duration, e.g. `[PAUSE:30]`. The TTS pipeline replaces this tag with actual silence of that length.

**Placement rules:**
- `[PAUSE:30]` immediately after `[PART:1]`, `[PART:2]`, `[PART:3]` (30 sec = time to read that part's full question set).
- `[PAUSE:20]` at any internal question-group boundary within a part (e.g. between Q1–5 and Q6–10 if they carry separate instructions).
- **No pause tag before `[PART:4]`** — it runs on directly from Part 3 with no gap, unlike Parts 1–3.
- No pause tag needed at the very end of Part 4 — the 10-minute answer-transfer period happens outside the script/audio.

**Example structure:**
```
[PART:1]
[PAUSE:30]
Speaker A: ...
Speaker B: ...

[PART:2]
[PAUSE:30]
Speaker A: ...

[PART:3]
[PAUSE:30]
Speaker A: ...
Speaker B: ...
[PAUSE:20]
Speaker A: ...

[PART:4]
Speaker A: ...
```

---

## 5. Core Rule for ALL Question Types (shared with Reading)

> **Every answer must be clearly derivable from what is stated in the recording**, at one identifiable point, in the order the questions are presented.

> **Question wording should paraphrase the audio content**, not lift it verbatim. Proper nouns, numbers, and technical terms may remain as spoken.

---

## 6. Quick Checklist Before Finalizing a Listening Question Set

- [ ] 4 parts, 10 questions each, 40 total
- [ ] Part 1–2 = everyday/social; Part 3–4 = educational/academic
- [ ] Part 1 & 3 = multi-speaker; Part 2 & 4 = monologue
- [ ] Each part's word count falls within its target range (Section 1 table)
- [ ] Questions strictly follow the order of information in the script
- [ ] Word limits explicitly stated wherever recording-derived answers are required
- [ ] No contracted words used as required answers
- [ ] Hyphenated words treated as single words in word-limit counting
- [ ] Numbers/names/spellings unambiguous in the script
- [ ] Distractor content in the script is natural, not random noise
- [ ] No outside/specialist knowledge required
- [ ] Difficulty progresses Part 1 (easiest) → Part 4 (hardest)
- [ ] `[PART:N]` tags present for all 4 parts, in order
- [ ] `[PAUSE:seconds]` tags present after `[PART:1/2/3]` and at internal question-group boundaries
- [ ] **No** pause tag before `[PART:4]`

---

## 7. GENERATOR AGENT — Listening-Specific Additions

### 7.1 Required Output
1. **Script** — full transcript, speaker-labeled, using `[PART:N]` and `[PAUSE:seconds]` tags exactly as specified in Section 4.1. Follow per-part word-count targets (Section 1).
2. **Instructions block** per question group, including exact word-limit phrasing.
3. **Questions**, numbered 1–40 continuously across all 4 parts.
4. **Answer key** — exact accepted answer(s), including acceptable spelling/format variants.
5. **Self-declared metadata** — for every answer: exact script location (Part/Speaker/line) where stated, confirmation it fits the word limit as spoken with no form change, and word count achieved per part vs. target.

### 7.2 Generation Rules
- Write natural spoken dialogue/monologue, not prose — realistic hesitations, rephrasing, natural turn-taking.
- Build in at least one natural spoken distractor per gap-fill/short-answer section where appropriate, without making the final answer ambiguous.
- Spell out or repeat any name/number that could be misheard.
- Explicitly verify question-order alignment with script-order before finalizing.
- Confirm no answer requires word-form change from what's spoken, unless trivial/unavoidable.
- Use `[PAUSE:seconds]` tags exactly per Section 4.1 — never describe pauses in prose.

### 7.3 Revision Behavior (on Evaluator FAIL)
- Address every flagged issue individually — don't regenerate from scratch unless a systemic issue is flagged.
- Preserve passing questions unchanged.
- Re-declare metadata after revision.
- If the issue is script ambiguity, fix the script itself — don't just alter the answer key to match a flawed script.

---

## 8. EVALUATOR AGENT — Listening-Specific Additions

### 8.1 Structural Checks (Step A)
- [ ] Script divided into exactly 4 parts, 10 questions each, 40 total
- [ ] Part 1 & 3 = 2+ speakers; Part 2 & 4 = 1 speaker
- [ ] Part 1–2 context = everyday/social; Part 3–4 = educational/academic
- [ ] Question numbering 1–40 continuous, matches script order
- [ ] `[PART:N]` tag present for all 4 parts, correctly numbered and in order
- [ ] `[PAUSE:seconds]` tag (exact format, not prose) present after `[PART:1]`, `[PART:2]`, `[PART:3]`
- [ ] `[PAUSE:seconds]` tag present at internal question-group boundaries
- [ ] **No** pause tag before `[PART:4]` — flag as Major if present
- [ ] Each part's word count falls within its target range — flag as Major if significantly off, since this affects generated audio duration

### 8.2 Independent Verification (Step B)
- Read the full script independently; locate each answer's exact position **before** looking at the Generator's key.
- Compare independently-derived answer to the Generator's key — any mismatch is Critical.
- Confirm each answer is stated only once, unambiguously, at the expected sequential position.

### 8.3 Type-Specific Checks (Step C)
- **Gap-fill types:** word limit stated; answer fits as spoken with no form change; no contractions; hyphenated words counted correctly.
- **Matching:** option count is fair (not trivially few, not ambiguous).
- **Multiple Choice:** exactly one correct answer among 3 options unless instructions state otherwise.

### 8.4 Error Taxonomy

| Severity | Example |
|---|---|
| **Critical** | Answer key wrong/unverifiable; requires word-form change from spoken form; script contradicts stated answer |
| **Major** | Missing word-limit instruction; questions out of script-order sequence; unspelled ambiguous name/number; missing required `[PAUSE:seconds]` tag; pause tag incorrectly present before `[PART:4]`; part word count significantly off target |
| **Minor** | Slightly unnatural dialogue phrasing; inconsistent speaker labeling format |

### 8.5 Feedback Format
```
Question [N] — [Severity]
Issue: [what's wrong]
Evidence: [script excerpt/location, e.g. "Part 2, Speaker A, ~line 14"]
Required fix: [specific instruction]
```
Plus top-line: `Verdict: FAIL — 1 Critical, 2 Major, 0 Minor`

### 8.6 Constraints
- Never defer to the Generator's stated answer key — independent derivation is mandatory.
- Always cite script location when flagging an issue.
- Don't flag stylistic preferences as Major/Critical.
- Script-level internal inconsistencies get flagged Critical with note "script-level issue" — may need full regeneration, not a patch.
- Max 3 revision rounds; escalate to human review with full evaluation history if still failing after that.

---

## 9. Division of Responsibility

| Task | Generator | Evaluator |
|---|---|---|
| Write script (incl. `[PART]`/`[PAUSE]` tags) | ✅ | — |
| Ensure natural spoken style | ✅ | ✅ (verify) |
| Write questions | ✅ | — |
| Propose answer key | ✅ | — |
| Re-derive answers independently from script | — | ✅ |
| Check word limits & spoken-form compliance | ✅ (self-check) | ✅ (verify) |
| Check question/script sequence alignment | ✅ (self-check) | ✅ (verify) |
| Check per-part word count vs. target | ✅ (self-check) | ✅ (verify) |
| Check tag placement/format correctness | ✅ (self-check) | ✅ (verify) |
| Decide PASS/FAIL | — | ✅ |
| Revise flagged items | ✅ | — |
| Escalate to human | — | ✅ (after max retries) |
