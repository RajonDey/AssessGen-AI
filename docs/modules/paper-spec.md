# Paper spec — per-part topics + interlocking question types

British Council–style papers use **independent topics per part**. Question types
**interlock across the paper** (diversify official item types). Writing Task 1 and
Task 2 do **not** share an item-type pool.

## Request shape (`POST /generate`)

| Module | Topics | Type plan / kinds |
|--------|--------|-------------------|
| Listening | `topics[4]` | `type_plan[4]` — Parts 1–3: 2–3 types; Part 4: exactly one notes type |
| Reading | `topics[3]` | `type_plan[3]` — 2–3 types each, diversified across passages |
| Writing | `topic_t1`, `topic_t2` (or `topics[2]`) | `task1_kind` + `task2_kind` (no shared pool) |

`topic` remains the primary/display topic (usually Part 1 / Task 1). When `topics` /
`type_plan` are omitted, the API autofills: topics copy `topic` per slot (compat);
`type_plan` uses BC-typical defaults from `app.content.paper_spec`.

### Listening defaults

1. `form_completion` + `note_completion`
2. `mcq_single` + `map_labelling`
3. `mcq_single` + `matching`
4. `note_completion` only

### Reading defaults (diversified, not a fixed BC matrix)

1. TFNG + sentence completion + short answer  
2. Matching headings + summary completion  
3. YNNG + MCQ + feature match  

### Writing kinds

- **task1_kind:** `line_graph` | `bar_chart` | `pie_chart` | `table` | `process` | `map` | `mixed` | letter registers  
- **task2_kind:** same enum as `writing_type` (`opinion`, `discussion`, …)

## Linking behaviour

Multi-part Reading/Listening still generate sequentially. Later parts receive:

- prior `question_types_used` (and the planned `type_plan` for the current part)
- numbering / difficulty / no answer-leakage instructions

They do **not** receive “sub-topic of main theme” instructions. Each part’s `topic`
field is taken from `topics[part - 1]`.

## Validation codes

| Code | Meaning |
|------|---------|
| `SPEC-TOPICS-LEN` | `topics` length ≠ part count |
| `SPEC-TYPEPLAN-LEN` | `type_plan` length ≠ part count |
| `SPEC-L4-NOTES` / `SPEC-L4-ONE-TYPE` | Listening Part 4 must be a single notes type |
| `SPEC-L-TYPE-COUNT` / `SPEC-R-TYPE-COUNT` | Wrong number of types for that part |
| `SPEC-TYPEPLAN-DUP` | Identical type sets on every part |
| `SPEC-TASK1-KIND` / `SPEC-TASK2-KIND` | Invalid Writing kind |

Implementation: `backend/app/content/paper_spec.py`, fields on `GenerateRequest`.

## Generate downloads (admin)

Tabs: **PDF · MD** only.

| Tab | Audience | Contents |
|-----|----------|----------|
| PDF | External | Paper = questions + answer key only (no visual briefs). Listening: optional script PDF |
| MD | Development | Full paper including visual/image briefs. Listening: script MD + **TTS JSON** (Kokoro) |

No full-paper JSON download. Listening TTS JSON is the only JSON export (`speakers` + `script.turns`).
