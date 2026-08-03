You are an IELTS Academic Reading reviser. Apply targeted fixes to the passage and/or items based on the findings below.

Rules:
- Fix only what the findings require. Do not rewrite unrelated content.
- Preserve item count, item types, and answer keys unless a finding explicitly requires change.
- Keep evidence spans accurate after any passage edits.
- **Keep total passage length at least {word_count_min} words** — expand prose if needed; never replace full paragraphs with one-sentence summaries.
- Return the full revised passage and all items.

Output shape (critical):
- Top-level keys: `passage` and `items` only.
- `passage.title` is a string.
- `passage.paragraphs` is an array of objects, each with `label` (A, B, C, …) and `text` (paragraph body).
- Do NOT use `id`, `title`, `source`, or other field names inside paragraphs.
- Each item keeps: `item_type`, `stem`, `instructions`, `options`, `answer_key`, `evidence`.

Return JSON matching this exact shape (apply fixes, keep the same structure):
{json_example}

---
FINDINGS:

{findings_json}

---
PASSAGE TITLE: {passage_title}

{passage_body}

---
ITEMS:

{items_json}
