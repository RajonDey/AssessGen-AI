"""Tests for Academic Reading continuous numbering (1–40)."""

from __future__ import annotations

from app.content.reading_numbering import (
    apply_reading_part_numbering,
    reading_question_range,
    renumber_reading_document,
)
from app.pipeline import merge_reading_parts
from app.rules.structure import evaluate_structure


def _section(
    *,
    title: str,
    q_start: int,
    count: int,
    words: str = "word " * 800,
) -> dict:
    questions = [{"number": q_start + i, "type": "text", "label": str(q_start + i)} for i in range(count)]
    return {
        "title": title,
        "passage": [words.strip()],
        "questionGroups": [
            {
                "id": "g1",
                "instruction": f"Questions {q_start}–{q_start + count - 1}. Write NO MORE THAN TWO WORDS.",
                "questions": questions,
            }
        ],
    }


def test_reading_question_ranges() -> None:
    assert reading_question_range(1) == (1, 13)
    assert reading_question_range(2) == (14, 26)
    assert reading_question_range(3) == (27, 40)


def test_renumber_document_shifts_ranges_and_items() -> None:
    doc = "## Questions 1–5\n\n1. foo\n2. bar\n| 3 | ans |\n**4. __________**"
    out = renumber_reading_document(doc, start_number=14)
    assert "Questions 14–18" in out
    assert out.startswith("## Questions") or "14–18" in out
    assert "14. foo" in out
    assert "15. bar" in out
    assert "| 16 |" in out
    assert "**17. " in out


def test_apply_part2_numbering_from_local_ones() -> None:
    part = {
        "type": "reading",
        "document": "Questions 1–13\n\n1. a\n13. z",
        "sections": [_section(title="P2", q_start=1, count=13)],
        "answer_key": {"1": "a", "13": "z"},
    }
    out = apply_reading_part_numbering(part, part_number=2)
    assert out["answer_key"]["14"] == "a"
    assert out["answer_key"]["26"] == "z"
    assert out["sections"][0]["questionGroups"][0]["questions"][0]["number"] == 14
    assert "Questions 14–26" in out["document"]


def test_merge_reading_parts_continuous_keys() -> None:
    parts = [
        {
            "type": "reading",
            "document": "Questions 1–13\n\n1. one",
            "sections": [_section(title="One", q_start=1, count=13)],
            "answer_key": {str(i): f"a{i}" for i in range(1, 14)},
        },
        {
            "type": "reading",
            "document": "Questions 1–13\n\n1. two",
            "sections": [_section(title="Two", q_start=1, count=13)],
            "answer_key": {str(i): f"b{i}" for i in range(1, 14)},
        },
        {
            "type": "reading",
            "document": "Questions 1–14\n\n1. three",
            "sections": [_section(title="Three", q_start=1, count=14, words="word " * 950)],
            "answer_key": {str(i): f"c{i}" for i in range(1, 15)},
        },
    ]
    merged = merge_reading_parts(parts)
    assert merged["parts_linked"] == 3
    assert merged["answer_key"]["1"] == "a1"
    assert merged["answer_key"]["14"] == "b1"
    assert merged["answer_key"]["27"] == "c1"
    assert merged["answer_key"]["40"] == "c14"
    assert "S1:" not in "".join(merged["answer_key"])
    # Document Part 2/3 must not keep Questions 1– after merge
    assert merged["document"].count("Questions 1–") == 1
    assert "Questions 14–26" in merged["document"]
    assert "Questions 27–40" in merged["document"]

    report = evaluate_structure("reading", merged)
    codes = {f.code for f in report.findings}
    assert "R-NUM" not in codes
    assert "R-QC-TOTAL" not in codes


def test_structure_flags_restarted_numbering() -> None:
    bad = {
        "type": "reading",
        "parts_linked": 2,
        "document": (
            "## Reading Section 1\n\nQuestions 1–13\n\n---\n\n"
            "## Reading Section 2\n\nQuestions 1–13\n"
        ),
        "sections": [
            _section(title="One", q_start=1, count=13),
            _section(title="Two", q_start=1, count=13),
        ],
        "answer_key": {"S1:1": "a", "S2:1": "b"},
    }
    report = evaluate_structure("reading", bad)
    codes = {f.code for f in report.findings}
    assert "R-NUM" in codes
    assert "R-KEY-NUM" in codes
