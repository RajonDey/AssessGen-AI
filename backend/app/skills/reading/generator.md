# IELTS Reading — Generator Agent Specification

Companion to `question_creation_reference.md`. That file is the shared rulebook for question creation. This file defines the generator agent role, its inputs/outputs, and revision behavior.

## Output Format

Prefer clear **Markdown** with headings, instructions, and numbered questions. Valid **JSON** matching the skill schema is also acceptable. Always include an answer key section.

---

## 1. Role

Produces one complete IELTS Reading passage + question set + answer key, fully compliant with `question_creation_reference.md`.

---

## 2. Required Inputs

- Passage number/slot (1, 2, or 3) or GT section — determines target length/difficulty
- Topic (given or self-selected if open)
- Question types to include (or "select appropriate types" if open)
- Number of questions required for this passage (typically 13–14)

---

## 3. Required Output (structured)

1. **Passage** — title, paragraph-labeled body (A, B, C… if needed for matching types), word count stated
2. **Instructions block** per question group (e.g., "Questions 1–5: Do the following statements agree with...")
3. **Questions** grouped by type, numbered continuously across the whole set
4. **Answer key** — exact accepted answer(s) per question, including acceptable variants
5. **Self-declared metadata**:
   - Word count of passage
   - Question types used and count of each
   - For each answer: paragraph/line reference where it's supported

---

## 4. Generation Rules

- Follow every rule in `question_creation_reference.md` sections 2–5 without exception.
- Build the **answer key simultaneously** with the questions — never write a question before confirming its answer exists verifiably in the passage.
- When using Matching Headings/Sentence Endings, generate the **distractor options first**, then confirm no distractor accidentally also fits another paragraph/stem correctly.
- When using NOT GIVEN / NO items, deliberately verify the passage neither states nor implies the claim — do not include it just because it "sounds plausible."
- Self-check word limits on every completion-type answer before output.
- If a generation attempt cannot satisfy a rule (e.g., can't find a genuine NOT GIVEN case), substitute a different question rather than force a weak one.

---

## 5. Revision Behavior (on Evaluator FAIL)

- Address **every** flagged issue individually — do not regenerate the whole set from scratch unless Evaluator flags a systemic issue (e.g., passage too short, wrong register).
- Preserve all passing questions unchanged; only touch flagged ones.
- Re-declare metadata after revision (updated answer key, updated references).

---

## 6. Word Count Targets

| Passage Position | Target Word Count |
| ---------------- | ----------------- |
| Passage 1        | ~750–850 words    |
| Passage 2        | ~850–950 words    |
| Passage 3        | ~900–1,050 words  |

---

## 7. Question Count

Each passage should have approximately **13–14 questions**, distributed across 2–3 question types.

---

## 8. Multi-Part Linking Rules

When generating a part that follows previous parts (current_part > 1), ensure:

### 8.1 Topic Coordination
- **Different sub-topic**: Each part should cover a different aspect of the main theme
- **No topic overlap**: Avoid discussing the same specific content across parts
- **Progressive depth**: Later parts can explore more specialized aspects

### 8.2 Question Type Variety
- **Different types**: Use different question types than previous parts
- **Check previous types**: Review `question_types_used` from previous parts
- **Balance coverage**: Ensure all major question types appear across the full test

### 8.3 Difficulty Progression
- **Increase complexity**: Later parts should be progressively harder
- **Vocabulary level**: More sophisticated vocabulary in later parts
- **Abstract concepts**: More abstract/argumentative content in later parts

### 8.4 Answer Isolation
- **No answer leakage**: Answering one part should not reveal answers to another
- **Independent passages**: Each passage stands alone without requiring knowledge of others
- **Distinct content**: Different facts, examples, and evidence across parts

### 8.5 Metadata Linking
When generating a linked part, include in your metadata:
```json
{
  "part_number": 2,
  "linked_to": "session_id",
  "previous_topics": ["topic from part 1"],
  "previous_question_types": ["types used in part 1"],
  "topic_variation": "how this part differs"
}
```
