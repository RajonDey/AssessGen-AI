You write IELTS Academic Reading matching-headings items.

PASSAGE
Title: {passage_title}
{passage_body}

TASK
- Item type: heading_match
- Paragraph count: {paragraph_count}
- Provide MORE headings than paragraphs (include distractors).
- One correct heading per paragraph; bijection required.

CONSTRAINTS (automatically verified):
- Headings must be noun phrases, not full sentences.
- Headings must not copy paragraph opening lines verbatim.
- Headings must not repeat each other.

Return JSON with ONE item in `items`:
- `item_type`: "heading_match"
- `stem`: brief instruction line
- `options`: list of heading strings (including distractors)

Do NOT include the answer mapping yet.
