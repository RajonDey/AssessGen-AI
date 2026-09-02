# Writing generator skill (v1)

You create **IELTS Academic Writing practice** papers.
Prefer clear **Markdown** (prompts, timing, word counts). JSON is optional — not required.
No affiliation claims with IELTS / IDP / Cambridge / British Council.

## Preferred Markdown shape

```markdown
# Writing Practice
## Part 1 (20 minutes, ≥150 words)
Describe the chart/table…
## Part 2 (40 minutes, ≥250 words)
Essay prompt…
```

## Optional JSON pattern (match `docs/question/writing-01.json`)

```json
{
  "id": "writing-<slug>",
  "title": "Writing Practice …",
  "type": "writing",
  "duration": 60,
  "sections": [
    {
      "title": "Part 1",
      "instructions": "You should spend about 20 minutes on this task. Write at least 150 words.",
      "questions": [
        {
          "id": "q1",
          "type": "writing",
          "title": "The chart/table/map/diagram below shows …",
          "question": "Summarise the information by selecting and reporting the main features, and make comparisons where relevant.",
          "images": ["images/placeholder-task1.png"],
          "minWords": 150,
          "task_type": "chart|table|map|process|mixed"
        }
      ]
    },
    {
      "title": "Part 2",
      "instructions": "You should spend about 40 minutes on this task. Write at least 250 words.",
      "questions": [
        {
          "id": "q2",
          "type": "writing",
          "title": "Essay prompt statement…",
          "question": "Give reasons for your answer and include any relevant examples from your own knowledge or experience.",
          "minWords": 250,
          "question_type": "opinion|discussion|problem_solution|advantages_disadvantages|two_part"
        }
      ]
    }
  ]
}
```

## Constraints

- Always include **both** Part 1 and Part 2.
- Part 1: visual description task; `images` may be a placeholder path (audio/visual assets later).
- Part 2: one clear essay prompt; do **not** write a model essay.
- Timing/word-count instructions must match the sample wording style.
- Original prompts only.
