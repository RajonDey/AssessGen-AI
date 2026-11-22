# Module — Writing

## The honest framing

Writing inverts the economics of every other module.

**Generating the task is easy.** A Task 2 prompt is two or three sentences; a Task 1 description is a
short instruction plus a data description. A small local model handles this comfortably.

**Everything valuable around the task is hard.** The model answers, the band justification, the
examiner commentary — these are what actually help a learner, and they are precisely what we cannot
currently verify. Writing a convincing "Band 7 model answer" requires knowing what Band 7 is, and
without an examiner we cannot confirm we do.

So this module's design must be unusually careful about what it claims. The tasks are production
content. The band-labelled model answers are, initially, **clearly-labelled estimates**.

---

## Format specification

### Academic

| Task | Type | Words | Time | Weight |
|------|------|-------|------|--------|
| 1 | Describe visual data — graph, chart, table, diagram, process, map | ≥ 150 | ~20 min | 1/3 |
| 2 | Discursive essay responding to a proposition | ≥ 250 | ~40 min | 2/3 |

### General Training

| Task | Type | Words | Time |
|------|------|-------|------|
| 1 | Letter — formal, semi-formal or informal | ≥ 150 | ~20 min |
| 2 | Essay, in a less formal register than Academic | ≥ 250 | ~40 min |

### Task 2 question types

| Type | Prompt pattern |
|------|---------------|
| Opinion | "To what extent do you agree or disagree?" |
| Discussion | "Discuss both views and give your own opinion." |
| Problem–solution | "What are the causes and what solutions can you suggest?" |
| Advantages–disadvantages | "Do the advantages outweigh the disadvantages?" |
| Two-part question | Two direct questions to answer |

### Task 1 Academic visual types

Line graph · bar chart · pie chart · table · process diagram · map comparison · mixed (two visuals).

⚠️ **Task 1 Academic requires a visual asset, and that is the module's real constraint.** We are not
generating images with an LLM. The approach is to generate **structured data** and render it
deterministically:

```json
{
  "chart_type": "line",
  "title": "Household internet access in four countries, 2000–2020",
  "x_axis": {"label": "Year", "values": [2000, 2005, 2010, 2015, 2020]},
  "series": [
    {"name": "Japan", "values": [30, 52, 71, 83, 91], "unit": "%"}
  ]
}
```

Rendered with matplotlib or Vega-Lite. This gives us three things a generated image could not:
the data is **verifiable** (so the model answer's factual claims can be checked deterministically),
the chart is **reproducible**, and it is **accessible** — the underlying numbers exist as data.

This turns the hardest-seeming part of Task 1 into the most machine-checkable part of the whole
Writing module.

---

## Pipeline

```
request { task, variant, topic_t1, topic_t2, task1_kind, task2_kind, target_band }
    # see docs/modules/paper-spec.md — independent Task 1 / Task 2 topics + kinds
    │
    ▼
TASK GENERATOR
  Task 1 Academic → chart spec (structured data) + instruction
  Task 1 GT       → letter scenario + three bullet requirements
  Task 2          → proposition + question type
    │
    ▼
QUALITY L0-L2 on task
  R-WRIT-001..009 · originality · dedup
    │
    ▼
CHART RENDERER          (Task 1 Academic only — deterministic, from data)
    │
    ▼
MODEL ANSWER GENERATOR  (one per target band: 6, 7, 8, 9)
    │
    ▼
BAND JUSTIFICATION      per official criterion, with evidence quoted from the answer
    │
    ▼
QUALITY L0-L2 on answers
  word count · criterion coverage · factual accuracy vs chart data
    │
    ▼
CRITIC ──▶ REVISER (bounded)
    │
    ▼
HUMAN REVIEW ──▶ approved
```

---

## Task quality rules

| Code | Severity | Check |
|------|----------|-------|
| `R-WRIT-001` | must | Task 2 prompt states a clear, arguable proposition |
| `R-WRIT-002` | must | The question type is answerable as phrased (a "discuss both views" prompt presents two views) |
| `R-WRIT-003` | must | Word-count instruction present and correct for the task |
| `R-WRIT-004` | should | Topic is culturally neutral and globally accessible |
| `R-WRIT-005` | should | Topic does not require specialist knowledge |
| `R-WRIT-006` | must | GT Task 1 letters specify recipient, purpose and exactly three bullets |
| `R-WRIT-007` | must | Task 1 Academic chart data is internally consistent (percentages sum, trends match labels) |
| `R-WRIT-008` | should | Chart contains a describable trend — flat, featureless data makes an unanswerable task |
| `R-WRIT-009` | should | Prompt avoids politically or religiously divisive framing |

`R-WRIT-004`, `-005` and `-009` are quality rules with a fairness purpose. An IELTS task that assumes
familiarity with one country's institutions disadvantages candidates unfairly, and it is an easy trap
for a model trained predominantly on Western text.

`R-WRIT-007` and `-008` are only possible because the chart is data rather than an image — a concrete
payoff from that design choice.

---

## Model answers and band labelling

### The problem, stated directly

⚠️ **We cannot currently verify that a "Band 7 model answer" is actually Band 7.** Producing
band-differentiated writing requires deliberately introducing controlled weaknesses — a Band 6 answer
needs limited lexical range and noticeable errors that still communicate — and judging whether the
result lands on the target requires examiner expertise the team does not have.

### What we do instead

**1. Generate against the official criteria explicitly.** The four public IELTS Writing criteria are
published descriptors, and using them is legitimate (cite the source):

| Criterion | Weight |
|-----------|--------|
| Task Achievement / Task Response | 25 % |
| Coherence and Cohesion | 25 % |
| Lexical Resource | 25 % |
| Grammatical Range and Accuracy | 25 % |

Each model answer is generated with per-criterion targets, not a single band number.

**2. Require a structured, evidenced justification.** The generator must justify its band claim
against each criterion, quoting the answer:

```json
{
  "target_band": 7,
  "criteria": {
    "lexical_resource": {
      "band": 7,
      "justification": "Uses less common vocabulary with some awareness of style ('mitigate', 'proliferation'), with occasional inaccuracy ('do a solution').",
      "evidence": ["mitigate the effects", "do a solution to this problem"]
    }
  }
}
```

The evidence quotes are machine-checkable: `R-ANS-004` verifies each quote appears verbatim in the
answer. That does not verify the *band judgement*, but it does eliminate fabricated justification —
which is the most common failure mode and would otherwise be invisible.

**3. Check what is deterministically checkable.**

| Code | Severity | Check |
|------|----------|-------|
| `R-ANS-001` | must | Word count meets the minimum for the task |
| `R-ANS-002` | must | The answer addresses every part of the prompt |
| `R-ANS-003` | must | Task 1 factual claims match the chart data **exactly** |
| `R-ANS-004` | must | Every justification quote appears verbatim in the answer |
| `R-ANS-005` | should | Lexical diversity (type–token ratio) increases monotonically across bands |
| `R-ANS-006` | should | Mean sentence complexity increases monotonically across bands |
| `R-ANS-007` | should | Error density decreases monotonically across bands |
| `R-ANS-008` | must | Band 9 answers contain no detectable grammatical errors |

`R-ANS-005..007` are the useful insight here. We cannot verify that a given answer *is* Band 7, but we
**can** verify that the Band 6 answer is measurably simpler than the Band 7, which is measurably
simpler than the Band 8. **Monotonic ordering is checkable even when absolute placement is not** — and
a set that fails monotonicity is definitely wrong, which is real signal for free.

`R-ANS-003` is only possible because Task 1 charts are data. A model answer claiming "sales peaked in
2015" is checked against the actual series. This is one of the few places in Writing where we get
Reading-grade certainty.

### Labelling policy

Until an examiner validates a sample, band labels on model answers are shown in the product as
**"estimated band"** with an explanatory note. This is a product-integrity requirement, not a
disclaimer for lawyers: a learner who trusts a mislabelled Band 7 answer is actively harmed by it,
and that is worse than offering no label at all.

---

## Examiner commentary

For each model answer, generate the learner-facing material that makes it useful:

- Per-criterion strengths and weaknesses
- A vocabulary list with definitions and example usage
- Specific improvements that would raise the band, tied to criteria
- Common mistakes at that band level

This is genuinely valuable learner content and it is where a Writing module earns its keep — a task
prompt alone is nearly worthless, since prompts are freely available everywhere.

---

## Current helpers

Task topics and kinds (`task1_kind`, `task2_kind`) are resolved in `app.content.paper_spec`. `app.content.writing_brief` builds the visual/image brief kept in the development Markdown export and left out of the candidate PDF. See [Paper spec](paper-spec.md).

## Definition of done

- [ ] Task 2 generating across all five question types with the full quality gate
- [ ] Task 1 Academic with structured chart data and deterministic rendering
- [ ] Task 1 GT letters across all three registers
- [ ] Model answers at Bands 6–9 with structured, evidenced justifications
- [ ] `R-WRIT-*` and `R-ANS-*` implemented and unit tested
- [ ] Monotonicity checks passing across each band set
- [ ] Examiner commentary and vocabulary lists generated
- [ ] Band-labelling policy visibly applied in the UI

## Phasing

| Phase | Scope |
|-------|-------|
| 1 | Task 2 prompt generation only, with review. Proves the pipeline; genuinely useful alone |
| 2 | Task 1 Academic with chart data; model answers; band justification |
| 2+ | GT letters, examiner commentary, vocabulary lists |
| Later | Examiner validation pass → convert "estimated band" to a validated label |
