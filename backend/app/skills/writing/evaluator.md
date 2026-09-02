# Writing evaluator skill (v1)

Validate Writing practice content (Markdown, text, or JSON).
Judge usefulness for IELTS practice — exact JSON schema is not required.

## Must fail if

- Almost empty / no usable task prompts
- Missing both Task 1 and Task 2 when a full Writing paper was requested
- Word-count guidance clearly wrong when stated (Task 1 ≠ 150 / Task 2 ≠ 250)

## Should note

- Vague Task 2 prompts
- Task 1 that does not mention a visual
- Missing timing instructions

No numeric score — findings only (`passed`, `summary`, `findings[]`).
