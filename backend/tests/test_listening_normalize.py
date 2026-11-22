"""Tests for Listening JSON normalization."""

from __future__ import annotations

from app.content.listening_normalize import normalize_listening_content
from app.pipeline import _listening_revision_notes, _revision_limit
from app.config import Settings
from app.schemas.generation import GenerateRequest, ReviewFinding
from app.rules.structure import evaluate_structure


def test_normalize_promotes_group_type_and_instructions() -> None:
    content = {
        "type": "listening",
        "partNumber": 1,
        "answer_key": {"1": "Kaur", "2": "Meadow"},
        "parts": [
            {
                "partNumber": 1,
                "questionGroups": [
                    {
                        "type": "form_completion",
                        "instructions": "Write ONE WORD AND/OR A NUMBER.",
                        "questions": [
                            {"number": 1, "prompt": "Surname: ______"},
                            {"number": 2, "prompt": "Street: ______"},
                        ],
                    },
                    {
                        "type": "short_answer",
                        "instructions": "Write NO MORE THAN THREE WORDS.",
                        "questions": [
                            {"number": 3, "prompt": "Why?"},
                            {"number": 4, "prompt": "Where?"},
                        ],
                    },
                ],
            }
        ],
    }
    normalize_listening_content(content)
    g0 = content["parts"][0]["questionGroups"][0]
    g1 = content["parts"][0]["questionGroups"][1]
    assert g0["subInstructions"] == "Write ONE WORD AND/OR A NUMBER."
    assert g1["subInstructions"] == "Write NO MORE THAN THREE WORDS."
    assert {q["type"] for q in g0["questions"]} == {"form_completion"}
    assert {q["type"] for q in g1["questions"]} == {"short_answer"}


def test_terra_style_group_types_pass_l_types() -> None:
    """Group-level type + instructions (Terra climate draft shape) must clear L-TYPES."""
    import json
    import re
    from pathlib import Path

    path = Path(
        "/media/gourob/New Volume17/Gourob/AssessGen-AI/Reference-Docs/"
        "assessgen-listening-climate-change.md"
    )
    if not path.exists():
        return
    raw = path.read_text(encoding="utf-8")
    match = re.search(r"```json\s*(\{.*\})\s*```", raw, re.S)
    assert match
    content = json.loads(match.group(1))
    normalize_listening_content(content)
    report = evaluate_structure("listening", content, passage_slot=1)
    assert not any(f.code == "L-TYPES" for f in report.findings)
    assert not any(f.code == "L-INS" for f in report.findings)
    musts = [f for f in report.findings if f.severity == "must"]
    assert not musts, [f.message for f in musts]


def test_normalize_answer_key_list_to_dict() -> None:
    content = {
        "type": "listening",
        "answer_key": ["annual", "B", "Tuesday"],
        "answer_evidence": ["said annual", "option B", "on Tuesday"],
        "parts": [
            {
                "partNumber": 1,
                "questionGroups": [
                    {
                        "questions": [
                            {
                                "questionNumber": 1,
                                "questionText": "Fee type: ……",
                                "type": "short-answer",
                                "subInstructions": "ONE WORD ONLY",
                            }
                        ]
                    }
                ],
            }
        ],
    }
    normalize_listening_content(content)
    assert content["answer_key"] == {"1": "annual", "2": "B", "3": "Tuesday"}
    assert content["answer_evidence"]["1"] == "said annual"
    q = content["parts"][0]["questionGroups"][0]["questions"][0]
    assert q["number"] == 1
    assert q["prompt"] == "Fee type: ……"
    assert content["parts"][0]["questionGroups"][0]["subInstructions"] == "ONE WORD ONLY"


def test_invented_answer_fails_l_ver() -> None:
    content = {
        "type": "listening",
        "partNumber": 1,
        "speakers": [
            {"id": "N1", "role": "narrator", "gender": "female", "accent": "british"},
            {"id": "S1", "role": "clerk", "gender": "female", "accent": "british"},
            {"id": "S2", "role": "customer", "gender": "male", "accent": "british"},
        ],
        "script": {
            "turns": [
                {
                    "speaker": "N1",
                    "text": (
                        "Welcome to this IELTS-style Listening practice test. Recordings are "
                        "played once only. The test is in four parts. Now look at Part 1. "
                        "You will hear a conversation. First, look at questions 1 to 5."
                    ),
                },
                {"speaker": "PAUSE", "text": "[PAUSE:40]"},
                {"speaker": "N1", "text": "Now listen carefully and answer questions 1 to 5."},
                {
                    "speaker": "S1",
                    "text": (
                        "Good morning. Welcome to Willow Creek Park. The annual fee is fifty "
                        "pounds. Volunteers update the notice board every Tuesday morning near "
                        "the library. The workshop is on Thursday. Sign up on the website and "
                        "bring gloves. Parking is free beside the library entrance. " * 8
                    ),
                },
                {
                    "speaker": "S2",
                    "text": (
                        "Great, I'll take the annual option and join the planting group near "
                        "the library entrance after the workshop on Thursday. " * 6
                    ),
                },
                {
                    "speaker": "N1",
                    "text": "Before you hear the rest, look at questions 6 to 10.",
                },
                {"speaker": "PAUSE", "text": "[PAUSE:25]"},
                {"speaker": "N1", "text": "Now listen and answer questions 6 to 10."},
                {
                    "speaker": "S1",
                    "text": (
                        "The cafe serves tea after the workshop and option A is often correct "
                        "when you are unsure. Choose B for evening events and C for weekends. "
                        "The visitor centre opens at nine. " * 8
                    ),
                },
                {
                    "speaker": "N1",
                    "text": (
                        "That is the end of Part 1. You now have one minute to check your "
                        "answers to Part 1."
                    ),
                },
                {"speaker": "PAUSE", "text": "[PAUSE:60]"},
            ]
        },
        "parts": [
            {
                "partNumber": 1,
                "questionGroups": [
                    {
                        "groupRange": "1-5",
                        "subInstructions": "Write ONE WORD ONLY.",
                        "questions": [
                            {"number": i, "type": "note_completion", "prompt": f"Q{i}"}
                            for i in range(1, 6)
                        ],
                    },
                    {
                        "groupRange": "6-10",
                        "subInstructions": "Choose A, B or C.",
                        "questions": [
                            {
                                "number": i,
                                "type": "multiple_choice",
                                "prompt": f"Q{i}",
                                "options": ["A", "B", "C"],
                            }
                            for i in range(6, 11)
                        ],
                    },
                ],
            }
        ],
        "answer_key": {
            "1": "annual",
            "2": "Tuesday",
            "3": "Thursday",
            "4": "website",
            "5": "gloves",
            "6": "A",
            "7": "B",
            "8": "C",
            "9": "A playground",
            "10": "Local café",
        },
    }
    report = evaluate_structure("listening", content, passage_slot=1)
    messages = " ".join(f.message for f in report.findings if f.code == "L-VER")
    assert "playground" in messages.lower() or "café" in messages.lower() or "cafe" in messages.lower()
    assert not report.passed


def test_listening_revision_notes_mention_expansion() -> None:
    notes = _listening_revision_notes(
        [
            ReviewFinding(severity="must", message="too short", code="L-WC-CONTENT"),
            ReviewFinding(severity="must", message="bad key", code="L-KEY"),
        ],
        "base notes",
    )
    assert "CRITICAL LENGTH FIX" in notes
    assert "answer_key" in notes


def test_listening_revision_notes_mention_types_layout() -> None:
    notes = _listening_revision_notes(
        [ReviewFinding(severity="must", message="one type", code="L-TYPES")],
        "base notes",
        part_number=1,
    )
    assert "CRITICAL QUESTION LAYOUT FIX (Parts 1–3)" in notes
    assert "2–3 distinct question types" in notes
    assert "Map/plan/diagram labelling IS allowed" in notes


def test_listening_revision_notes_part4_single_type() -> None:
    notes = _listening_revision_notes(
        [ReviewFinding(severity="must", message="too many types", code="L-TYPES")],
        "base notes",
        part_number=4,
    )
    assert "CRITICAL QUESTION LAYOUT FIX (Part 4)" in notes
    assert "exactly ONE question type" in notes
    assert "2–3 distinct question types" not in notes


def test_listening_revision_notes_mention_map_brief() -> None:
    notes = _listening_revision_notes(
        [ReviewFinding(severity="must", message="no brief", code="L-MAP-BRIEF")],
        "base notes",
    )
    assert "CRITICAL MAP/PLAN VISUAL FIX" in notes
    assert "pending_vendor" in notes


def test_listening_revision_limit_raises_on_length() -> None:
    settings = Settings(max_revision_loops=2, listening_max_revision_loops=4)
    req = GenerateRequest(module="listening", topic="parks")
    limit = _revision_limit(
        settings,
        req,
        [ReviewFinding(severity="must", message="short", code="L-WC")],
    )
    assert limit == 4
