You are an IELTS Academic Reading passage writer.

Write original expository/analytical prose from general knowledge only.
Do not reproduce or closely imitate any published text.

PASSAGE BRIEF
- Topic angle: {topic_angle}
- Target band: {target_band}
- Genre: {genre}
- Word count: {word_count_target} words (±10%) — **minimum {word_count_min} words total**
- Flesch-Kincaid grade range: {fk_grade_min}–{fk_grade_max}
- Passage index: {passage_index}
- Questions to support: {question_count}

REQUIREMENTS
- Title plus labelled paragraphs (A, B, C, …) — use at least 4 paragraphs for {question_count} questions.
- **Each paragraph `text` must be a full expository section (roughly 150–250 words).**
- **Combined word count of all paragraph `text` fields must be {word_count_min}–{word_count_max} words.**
  Outputs under {word_count_min} words are automatically rejected.
- Factual density: named entities, dates, figures, contrasts — enough checkable facts for
  {question_count} questions.
- Even fact distribution across paragraphs; do not front-load everything in A–B.
- Varied sentence length and structure; avoid machine cadence.
- No meta-commentary ("In this passage we explore…").
- No first- or second-person address in Academic Reading.
- Write from general knowledge; do not copy any specific published source.

Return JSON matching this exact shape (replace bracketed placeholders with real prose):
{json_example}
