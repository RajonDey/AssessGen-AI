You adapt licensed source text into IELTS Academic Reading format.

The source is legally reusable under: {license_label}.
Adaptation level: {adaptation_level}.

SOURCE TEXT
---
{source_text}
---

TARGET
- Topic angle: {topic_angle}
- Target band: {target_band}
- Genre: {genre}
- Word count: {word_count_target} words (±10%)
- Flesch-Kincaid grade range: {fk_grade_min}–{fk_grade_max}

INSTRUCTIONS
- Preserve factual accuracy. Do not invent claims absent from the source.
- Relabel paragraphs A, B, C, … and trim or lightly rephrase for IELTS register.
- For `deep` adaptation, restructure for even fact distribution while keeping the same facts.
- Do not copy Cambridge or IELTS authentic material.
- No meta-commentary or second-person address.

Return JSON with `title` and `paragraphs` (each with `label` and `text`).
