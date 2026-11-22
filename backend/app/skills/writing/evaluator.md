# Writing evaluator skill (v1)

Validate Writing practice content (Markdown, text, or JSON).
Judge usefulness for IELTS practice — exact JSON schema is not required.

## Must fail if

- Almost empty / no usable task prompts
- Missing both Task 1 and Task 2 when a full Writing paper was requested
- Word-count guidance clearly wrong when stated (Task 1 ≠ 150 / Task 2 ≠ 250)
- Part 1 has no vendor-ready visual brief / scenario (images are optional — external vendor)

## Should note

- Vague Task 2 prompts
- Thin visual_brief (no chart type / data story / labels)
- Missing timing instructions
- Sample answers without **estimated band** labelling

No numeric score — findings only (`passed`, `summary`, `findings[]`).
