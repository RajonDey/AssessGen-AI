You produce the answer mapping for an IELTS Reading matching-headings item.

PASSAGE
Title: {passage_title}
---
{passage_body}
---

ITEM
{items_json}

Return ONE item with:
- `answer_key`: type "mapping", `values` maps each paragraph label (A, B, C, …) to the
  chosen heading text from `options`.
- `evidence`: null (heading match uses mapping, not evidence spans).
- `explanation`: one sentence per paragraph choice for reviewers.

CONSTRAINTS (automatically verified):
- R-HEAD-002: bijection — every paragraph mapped once, no duplicate headings.
- R-HEAD-003: every mapped paragraph label exists in the passage.

Return JSON with an `items` array containing exactly one answered item.
