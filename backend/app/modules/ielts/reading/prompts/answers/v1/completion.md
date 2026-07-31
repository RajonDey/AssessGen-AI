You produce answer keys and evidence spans for IELTS Reading completion items.

PASSAGE (character offsets are into this exact body string)
Title: {passage_title}
---
{passage_body}
---

ITEMS (stems only — derive answers from the passage)
{items_json}

For each item return:
- `answer_key`: type "exact", `values` (primary answer), optional `accept` alternates,
  `case_sensitive` false unless necessary.
- `evidence`: `paragraph` label, `start`/`end` character offsets into the passage body above,
  and `quote` where `body[start:end] == quote` exactly.
- `explanation`: one sentence for reviewers.

CONSTRAINTS (automatically verified):
- R-COMP-001: answer is a verbatim contiguous substring of the passage body.
- R-COMP-002: answer obeys the word limit in instructions.
- R-COMP-006: answer is not a bare function word (a, the, of, and, in).
- R-ITEM-005: evidence quote must match passage text at offsets.
- R-SET-006: each item tests a distinct fact.

Return JSON with an `items` array matching the input order and fields:
`item_type`, `stem`, `instructions`, `answer_key`, `evidence`, `explanation`.

Return JSON matching this exact shape (compute real offsets from the passage body above):
{json_example}
