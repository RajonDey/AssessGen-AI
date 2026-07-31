You write IELTS Academic Reading sentence-completion items.

PASSAGE
Title: {passage_title}
{passage_body}

TASK
- Item type: sentence_completion
- Count: {item_count}
- Target paragraphs for answers: {target_paragraphs}
- Instructions: {instructions}

CONSTRAINTS (automatically verified):
- Each answer MUST appear word-for-word in the passage.
- Each answer MUST obey the word limit in the instructions.
- Each stem MUST contain a gap (_____ or …).
- Do NOT include the answer in the stem.
- Do NOT test the same fact twice across items.
- Items should follow passage order where possible.

Return JSON with an `items` array. Each item: `item_type`, `stem`, `instructions`.
Do NOT include answer keys or evidence yet.

Return JSON matching this exact shape (field names and types must match):
{json_example}
