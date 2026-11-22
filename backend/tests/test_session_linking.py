"""Unit tests for multi-part reading session linking (no LLM)."""

from app.pipeline import _attach_session_context, merge_reading_parts
from app.schemas.generation import GenerateRequest
from app.sessions import SessionManager, extract_part_context


def test_extract_part_context_from_sections() -> None:
    content = {
        "title": "Urban Parks",
        "sections": [
            {
                "title": "Green corridors",
                "questionGroups": [
                    {
                        "questions": [
                            {"type": "true-false-not-given"},
                            {"type": "summary-completion"},
                        ]
                    }
                ],
            }
        ],
    }
    ctx = extract_part_context(content, part_number=1)
    assert "Urban Parks" in ctx["topics"]
    assert "Green corridors" in ctx["topics"]
    assert "true-false-not-given" in ctx["question_types"]
    assert "summary-completion" in ctx["question_types"]


def test_extract_part_context_from_document() -> None:
    content = {
        "document": (
            "# Bee decline\n\nChoose the correct letter, A, B, C or D.\n\n"
            "Do the following statements agree with the information "
            "(True/False/Not Given)?"
        ),
        "format": "markdown",
    }
    ctx = extract_part_context(content, part_number=2)
    assert ctx["part_number"] == 2
    assert "Bee decline" in ctx["topics"]
    assert "multiple-choice" in ctx["question_types"]
    assert "true-false-not-given" in ctx["question_types"]


def test_session_linking_context_aggregates() -> None:
    mgr = SessionManager()
    session = mgr.create_session("reading", "cities", 6.5, total_parts=3)
    session.add_part(
        {
            "title": "Parks",
            "sections": [
                {
                    "title": "Parks",
                    "questionGroups": [{"questions": [{"type": "short-answer"}]}],
                }
            ],
        }
    )
    session.add_part(
        {
            "document": "# Traffic\n\nComplete the summary below.\n",
            "format": "markdown",
        }
    )
    linking = session.get_linking_context()
    assert linking["parts_completed"] == 2
    assert "Parks" in linking["topics_covered"]
    assert "Traffic" in linking["topics_covered"]
    assert "short-answer" in linking["question_types_used"]
    assert "summary-completion" in linking["question_types_used"]
    summary = session.get_summary()
    assert "Part 1" in summary
    assert "Part 2" in summary


def test_attach_session_context_fills_previous() -> None:
    from app.sessions import session_manager

    session = session_manager.create_session("reading", "oceans", 7.0, total_parts=3)
    session.add_part({"title": "Coral reefs", "document": "# Coral reefs\n\n" + ("word " * 50)})

    req = GenerateRequest(
        module="reading",
        topic="oceans",
        session_id=session.session_id,
        current_part=1,
        total_parts=3,
    )
    updated = _attach_session_context(req)
    assert updated.current_part == 2
    assert updated.previous_content is not None
    assert "Coral reefs" in (updated.previous_content.get("topics_covered") or [])
    session_manager.delete_session(session.session_id)


def test_merge_reading_parts_documents_and_sections() -> None:
    parts = [
        {
            "type": "reading",
            "document": "Questions 1–1\n\n1. Section one body",
            "format": "markdown",
            "sections": [
                {
                    "title": "One",
                    "passage": ["word " * 800],
                    "questionGroups": [
                        {
                            "instruction": "Questions 1–1",
                            "questions": [{"number": 1, "type": "text", "label": "1"}],
                        }
                    ],
                }
            ],
            "answer_key": {"1": "TRUE"},
        },
        {
            "type": "reading",
            "document": "Questions 1–1\n\n1. Section two body",
            "format": "markdown",
            "sections": [
                {
                    "title": "Two",
                    "passage": ["word " * 900],
                    "questionGroups": [
                        {
                            "instruction": "Questions 1–1",
                            "questions": [{"number": 1, "type": "text", "label": "1"}],
                        }
                    ],
                }
            ],
            "answer_key": {"1": "FALSE"},
        },
    ]
    merged = merge_reading_parts(parts)
    assert merged["type"] == "reading"
    assert merged["parts_linked"] == 2
    assert len(merged["sections"]) == 2
    assert "Reading Section 1" in merged["document"]
    assert "Reading Section 2" in merged["document"]
    assert merged["answer_key"]["1"] == "TRUE"
    assert merged["answer_key"]["14"] == "FALSE"
    assert merged["sections"][1]["questionGroups"][0]["questions"][0]["number"] == 14

