You write IELTS Academic Reading note/table completion items.

PASSAGE
Title: {passage_title}
{passage_body}

TASK
- Item type: note_completion
- Count: {item_count}
- Target paragraphs for answers: {target_paragraphs}
- Instructions: {instructions}

CONSTRAINTS (automatically verified):
- Each answer MUST appear word-for-word in the passage.
- Each answer MUST obey the word limit.
- Notes/table rows MUST contain gaps (_____ or …).
- Do NOT leak answers in the stem.
- Do NOT test the same fact twice.

Return JSON with an `items` array. Each item: `item_type`, `stem`, `instructions`.
Do NOT include answer keys or evidence yet.
