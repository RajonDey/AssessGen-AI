# Module — Listening

## What makes this module different

Listening is the only module with a **binary artefact** and therefore the only one with a materially
different pipeline. Everything through script generation mirrors Reading; then audio synthesis adds a
stage that can fail in ways text never does.

The important structural insight: **the script is the source of truth, and questions are generated
from the script, not from the audio.** Audio is a rendering of the script. This means the entire
Reading quality apparatus — verbatim answer checks, evidence offsets, rule engine — applies unchanged
to the transcript. Audio QA then verifies only that the rendering is faithful.

That decision is what makes Listening tractable. If questions were derived from audio we would need
speech understanding in the quality loop, and no part of the deterministic gate would work.

---

## Format specification

| Section | Context | Speakers | Questions |
|---------|---------|----------|-----------|
| 1 | Everyday social — a transactional conversation (booking, enquiry) | 2 | 10 |
| 2 | Everyday social — a monologue (a talk, a guided tour) | 1 | 10 |
| 3 | Educational/training — a discussion | 2–4 | 10 |
| 4 | Academic — a lecture monologue | 1 | 10 |

- 40 questions, ~30 minutes of audio, plus 10 minutes transfer time.
- Audio plays **once only**. This is why script quality standards are stricter than Reading: a
  listener cannot re-read.
- Difficulty increases from Section 1 to Section 4.
- Accents vary — British, Australian, North American, New Zealand.

### Question types

| Type | `item_type` | Machine-checkable |
|------|-------------|-------------------|
| Form/note/table completion | `note_completion` | ★★★ verbatim in transcript |
| Sentence completion | `sentence_completion` | ★★★ |
| Short answer | `short_answer` | ★★★ |
| Multiple choice | `mcq_single` / `mcq_multi` | ★★☆ |
| Matching | `feature_match` | ★★☆ |
| Plan/map/diagram labelling | `map_label` | ★☆☆ needs an image asset |

Section 1 form-completion is the natural first implementation: highly structured, verbatim answers,
and it exercises the full audio pipeline on the simplest possible content.

---

## Pipeline

```
request { section, topic, accent, question_count }
    │
    ▼
PLANNER            section context, speaker roles, turn count, answer targets
    │
    ▼
SCRIPT GENERATOR   dialogue or monologue with speaker labels and turn offsets
    │
    ▼
QUALITY L0-L2 on script
  R-LIST-001..008 · originality · dedup
    │
    ▼
QUESTION + ANSWER GENERATOR   (evidence offsets into the TRANSCRIPT)
    │
    ▼
QUALITY L0-L2 on items        (reuses all Reading completion/MCQ rules)
    │
    ▼
CRITIC ──▶ REVISER (bounded)
    │
    ▼
HUMAN REVIEW (text only)      ← approve the script BEFORE spending TTS time
    │
    ▼
TTS SYNTHESIS   Kokoro · voice per speaker · natural inter-turn gaps
    │
    ▼
AUDIO QA        duration · silence · clipping · ASR round-trip fidelity
    │
    ▼
UPLOAD to S3/R2 ──▶ asset record ──▶ publishable
```

**Human review happens before synthesis, not after.** Synthesising audio for a script that a reviewer
then rejects wastes the most expensive step in the module. The reviewer approves text; audio is
generated from approved text only.

---

## Script generation

The script is what makes or breaks this module, and it has requirements Reading does not:

| Requirement | Why | Rule |
|-------------|-----|------|
| Natural spoken register | Written prose read aloud sounds obviously wrong | `R-LIST-002` |
| Hesitations, false starts, self-correction (Sections 1, 3) | Real IELTS audio contains them, and they are frequently tested | `R-LIST-003` |
| Answers **spread across the timeline** | Clustered answers make the task trivial | `R-LIST-005` |
| Answers spoken **exactly as they must be written** | The candidate transcribes what they hear | `R-LIST-001` |
| Distractor information before correction | "Tuesday — sorry, Wednesday" is a classic IELTS device | `R-LIST-006` |
| Speaker labels consistent throughout | Needed for voice assignment | `R-LIST-004` |
| Spellable proper nouns spelled out | "That's B-R-Y-C-E" — standard in Section 1 | `R-LIST-007` |
| Numbers/dates in natural spoken form | "oh seven nine four" not "0794" | `R-LIST-008` |

`R-LIST-006` — the self-correction distractor — is worth calling out. It is one of the most
characteristic features of authentic IELTS Listening and one a naive generator never produces
spontaneously. It must be an explicit prompt instruction with a rule verifying it appears.

### Script format

```json
{
  "section": 1,
  "context": "A customer enquiring about gym membership",
  "speakers": [
    {"id": "S1", "role": "receptionist", "gender": "female", "accent": "british"},
    {"id": "S2", "role": "customer", "gender": "male", "accent": "british"}
  ],
  "turns": [
    {"speaker": "S1", "text": "Good morning, Fitness First. How can I help?",
     "start_char": 0, "end_char": 44}
  ]
}
```

Character offsets serve exactly the role they do in Reading: evidence spans for answer verification.

---

## Text-to-speech

**Kokoro-82M**, Apache 2.0, running locally.

| Property | Value |
|----------|-------|
| Licence | Apache 2.0 — commercially usable, no restrictions |
| Size | 82 M params, ~330 MB weights |
| Hardware | CPU-capable, faster than real time |
| Output | 24 kHz |
| British English voices | 8 (`bf_alice`, `bf_emma`, `bf_isabella`, `bf_lily`, `bm_daniel`, `bm_fable`, `bm_george`, `bm_lewis`) |

**Why not XTTS v2:** it clones voices better, but ships under the Coqui Public Model License —
non-commercial only — and Coqui is defunct, so no commercial licence can be bought. It is a legal
dead end for a product. **Chatterbox** (MIT) is the fallback if voice cloning ever becomes a
requirement.

### Voice assignment

- Deterministic per speaker within a script; consistent for a whole test.
- Gender and accent respected from the speaker definition.
- Different voices for different speakers in the same section — obviously, but it needs asserting.
- ⚠️ **Accent coverage gap:** Kokoro provides British and American English. IELTS also uses
  Australian and New Zealand accents. This is a known limitation to disclose rather than paper over —
  the content is valid practice material but does not cover the full accent range of the real exam.

### Synthesis

- Per-turn synthesis, concatenated with randomised 250–500 ms gaps. Uniform gaps sound mechanical.
- Slightly longer pauses at section boundaries.
- Output: MP3 (delivery) plus WAV (archive).
- Runs on `q.audio` at concurrency 2 — CPU-bound, so it does not contend for the model lease.

---

## Audio QA

An automated gate no human should have to perform:

| Check | Method | Severity |
|-------|--------|----------|
| Duration within expected range | Word count ÷ speech rate | must |
| No clipping | Peak amplitude analysis | must |
| No excessive silence | Silence detection | should |
| Consistent loudness | LUFS normalisation | should |
| All turns present | Segment count vs script turns | must |
| **Answer words audible and correct** | **ASR round-trip** | **must** |

### The ASR round-trip

The single most valuable check in the module. Transcribe the generated audio with a local ASR model
and compare against the source script, focusing on the answer spans:

```
script answer: "photosynthesis"  →  TTS  →  ASR  →  "photo synthesis"  ❌ FAIL
```

If ASR cannot recover the answer word, a human listener plausibly cannot either — and the item is
unanswerable in a way that would be invisible to every text-based check. This catches TTS
mispronunciation of technical terms, proper nouns and unusual spellings, which is exactly where
Kokoro is weakest.

Implementation: `faster-whisper` with a small model, on the answer spans only. Whole-file
transcription is unnecessary and slow.

⚠️ Adds an ASR model to the memory budget. It runs on `q.audio` **after** generation completes, never
concurrently with the generator — audio QA is a separate stage precisely so the two never contend.

---

## Storage

```
s3://assessgen-media/
  listening/{passage_version_id}/
    audio.mp3
    audio.wav
    transcript.json
    qa_report.json
```

Assets are immutable and content-addressed. A new script version produces a new asset path — audio is
never overwritten, for the same reason content versions are not.

---

## Definition of done

- [ ] Section 1 and 2 scripts generating with the full quality gate
- [ ] Form/note completion and sentence completion working
- [ ] `R-LIST-001..008` implemented and unit tested
- [ ] Kokoro synthesis with correct multi-voice assignment
- [ ] Audio QA including ASR round-trip on answer spans
- [ ] Assets uploaded and served via signed URLs
- [ ] A full 4-section, 40-question Listening test published

## Phasing

| Phase | Scope |
|-------|-------|
| 1 | Script generation + text-only review. **No audio.** Proves the text pipeline |
| 3 | Kokoro synthesis, audio QA, asset pipeline |
| 3+ | Sections 3–4, map/diagram labelling, accent expansion |

Deferring audio to Phase 3 is deliberate: an approved script is already a useful artefact, and it
lets us validate the harder half of the module without taking on the memory and tooling cost of TTS
and ASR while the core pipeline is still settling.
