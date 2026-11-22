"""Reading markdown → structured sections/answer_key alignment."""

from __future__ import annotations

from app.content.reading_normalize import normalize_reading_content


_SAMPLE_MULTI = """
## Reading Section 1

# The Return of Practical Hobbies

### A
Practical hobbies are now more visible through workshops and online channels.

### B
Many participants began a hobby to save money, but continued because they enjoyed becoming more capable.

---

## Questions 1–2

### Do the following statements agree with the information given in Reading Passage 1?

In boxes **1–2** on your answer sheet, write:

- **TRUE** if the statement agrees with the information
- **FALSE** if the statement contradicts the information
- **NOT GIVEN** if there is no information on this

1. Practical hobbies have become easier to notice.
2. All interviewees began hobbies only to save money.

---

## Questions 3–4

### Complete the notes below.

Choose **ONE WORD ONLY** from the passage for each answer.

- Online **3. __________** can help people acquire techniques.
- People may gain a sense of **4. __________**.

# Answer Key

| Question | Answer | Passage reference |
|---|---|---|
| 1 | TRUE | Paragraph A |
| 2 | FALSE | Paragraph B |
| 3 | tutorials | Paragraph A |
| 4 | independence | Paragraph B |

## Metadata

- Passage number: 1

---

## Reading Section 2

# IELTS Academic Reading Practice — Part 2
### Questions 14–26

## Passage: When Leisure Moves Online

**Word count: approximately 200 words**

### A
Digital tools alter how people discover hobbies.

### B
Beginners can experiment before committing substantial money or time.

---

## Questions 14–15

### Reading Passage 2 has two paragraphs, A–B.

Choose the correct heading for each paragraph from the list of headings below.

### List of Headings

i. Trying new interests with limited commitment
ii. The difficulty of defining modern recreational activity

14. Paragraph A
15. Paragraph B

---

## Questions 16–17

### Choose the correct letter, **A, B, C or D**.

16. What does the writer suggest about online resources?

A. They replace formal classes completely.
B. They allow people to investigate an activity before committing.
C. They are only for experts.
D. They are unreliable.

17. What is mentioned about beginners?

A. They dislike clubs.
B. They need specialist magazines.
C. They can experiment online first.
D. They must buy equipment first.

# Answer Key

| Question | Answer | note |
|---|---|---|
| 14 | ii | A |
| 15 | i | B |
| 16 | B | B |
| 17 | C | B |

---

## Reading Section 3

## The Leisure of Measurement

### A
People keep records about leisure activities; this impulse is not new.

---

## Questions 27–28

### Do the following statements agree with the views of the writer?

- **YES** if the statement agrees with the views of the writer
- **NO** if the statement contradicts the views of the writer
- **NOT GIVEN** if it is impossible to say what the writer thinks about this

27. Digital technology is the original cause of record-keeping.
28. Observing routine activities can itself be pleasurable.

# Answer Key

| 27 | **NO** | Paragraph A |
| 28 | **YES** | Paragraph A |
""".strip()


def test_normalize_rebuilds_stub_sections_from_markdown() -> None:
    content = {
        "type": "reading",
        "format": "markdown",
        "parts_linked": 3,
        "document": _SAMPLE_MULTI,
        "sections": [
            {
                "title": "IELTS Academic Reading Practice — Part 1",
                "passage": [
                    "**You should spend about 20 minutes on Questions 1–13.**",
                    "**Word count: 812 words**",
                    "---",
                ],
                "questionGroups": [
                    {
                        "instruction": "Questions 1–2",
                        "questions": [
                            {"number": 1, "type": "text", "prompt": "stub"},
                        ],
                    }
                ],
            }
        ],
        "answer_key": {"1": "0", "7": "0"},
    }
    normalize_reading_content(content)
    assert len(content["sections"]) == 3
    s1, s2, s3 = content["sections"]
    assert "Practical Hobbies" in s1["title"] or "Return" in s1["title"]
    assert len(" ".join(s1["passage"]).split()) > 20
    assert [g["type"] for g in s1["questionGroups"]] == [
        "true_false_not_given",
        "note_completion",
    ]
    assert s1["questionGroups"][0]["groupRange"] == "1-2"
    assert s1["questionGroups"][1]["groupRange"] == "3-4"

    assert [g["type"] for g in s2["questionGroups"]] == [
        "matching_headings",
        "multiple_choice",
    ]
    mcq = s2["questionGroups"][1]["questions"][0]
    assert mcq["options"]["B"].startswith("They allow")

    assert s3["questionGroups"][0]["type"] == "yes_no_not_given"
    assert content["answer_key"]["1"] == "TRUE"
    assert content["answer_key"]["2"] == "FALSE"
    assert content["answer_key"]["3"] == "tutorials"
    assert content["answer_key"]["14"] == "ii"
    assert content["answer_key"]["16"] == "B"
    assert content["answer_key"]["27"] == "NO"
    assert content["answer_key"]["28"] == "YES"


def test_normalize_keeps_rich_sections_without_markdown() -> None:
    content = {
        "type": "reading",
        "sections": [
            {
                "title": "Coral",
                "passage": ["word " * 800],
                "questionGroups": [
                    {
                        "type": "true_false_not_given",
                        "instruction": "Questions 1–13",
                        "groupRange": "1-13",
                        "questions": [
                            {
                                "number": i,
                                "type": "true_false_not_given",
                                "prompt": f"Q{i}",
                            }
                            for i in range(1, 14)
                        ],
                    }
                ],
            }
        ],
        "answer_key": {str(i): "TRUE" for i in range(1, 14)},
    }
    normalize_reading_content(content)
    assert content["sections"][0]["title"] == "Coral"
    assert content["sections"][0]["questionGroups"][0]["type"] == "true_false_not_given"
