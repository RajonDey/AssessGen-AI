"""Structure rules for Knowledge-base-aligned question quality (notes/map/MCQ/banks)."""

from __future__ import annotations

from app.rules.structure import evaluate_structure


def _pad(n: int = 40) -> str:
    return ("word " * n).strip()


def test_listening_part4_notes_require_outline() -> None:
    content = {
        "type": "listening",
        "partNumber": 4,
        "speakers": [
            {"id": "N1", "role": "narrator", "gender": "female", "accent": "british"},
            {"id": "S1", "role": "lecturer", "gender": "male", "accent": "british"},
        ],
        "script": {
            "turns": [
                {"speaker": "N1", "text": "Now look at Part 4. Look at questions 31 to 40."},
                {"speaker": "PAUSE", "text": "[PAUSE:40]"},
                {"speaker": "N1", "text": "Now listen."},
                {"speaker": "S1", "text": f"Today we study sleep. {_pad(200)}"},
                {"speaker": "N1", "text": "Look at questions 37 to 40."},
                {"speaker": "PAUSE", "text": "[PAUSE:25]"},
                {"speaker": "N1", "text": "Now listen."},
                {"speaker": "S1", "text": f"Later findings show naps. {_pad(200)}"},
                {"speaker": "N1", "text": "That is the end of Part 4. Check your answers."},
                {"speaker": "PAUSE", "text": "[PAUSE:60]"},
            ]
        },
        "parts": [
            {
                "partNumber": 4,
                "questionGroups": [
                    {
                        "groupRange": "31-40",
                        "type": "note_completion",
                        "subInstructions": "Write ONE WORD ONLY.",
                        "questions": [
                            {
                                "number": i,
                                "type": "note_completion",
                                "notes": f"Fact line {i} uses ________ here.",
                            }
                            for i in range(31, 41)
                        ],
                    }
                ],
            }
        ],
        "answer_key": {str(i): "sleep" for i in range(31, 41)},
    }
    report = evaluate_structure("listening", content, passage_slot=4)
    assert any(f.code == "L-NOTES-OUTLINE" and f.severity == "must" for f in report.findings)


def test_listening_part4_notes_outline_passes() -> None:
    outline = {
        "title": "Sleep research",
        "sections": [
            {
                "heading": "Methods",
                "items": [
                    {"content": "Researchers tracked adults overnight", "hasInput": False},
                    {"content": "Each wore an (31) device", "hasInput": True},
                    {"content": "Records lasted (32) days", "hasInput": True},
                    {"content": "Diaries supported the devices", "hasInput": False},
                ],
            },
            {
                "heading": "Light and drink",
                "items": [
                    {"content": "Focus on (33) light after waking", "hasInput": True},
                    {"content": "Final (34) drink was logged", "hasInput": True},
                    {"content": "Baseline habits were surveyed", "hasInput": False},
                ],
            },
            {
                "heading": "Regularity",
                "items": [
                    {"content": "Measured using the (35) of sleep", "hasInput": True},
                    {"content": "Short naps under (36) minutes were mild", "hasInput": True},
                ],
            },
            {
                "heading": "Limits",
                "items": [
                    {"content": "Late (37) naps were worse", "hasInput": True},
                    {"content": "Devices may mistake quiet (38)", "hasInput": True},
                    {"content": "Sample was limited", "hasInput": False},
                    {"content": "Need more (39) studies", "hasInput": True},
                    {"content": "Future work on (40) age groups", "hasInput": True},
                ],
            },
        ],
    }
    content = {
        "type": "listening",
        "partNumber": 4,
        "speakers": [
            {"id": "N1", "role": "narrator", "gender": "female", "accent": "british"},
            {"id": "S1", "role": "lecturer", "gender": "male", "accent": "british"},
        ],
        "script": {
            "turns": [
                {"speaker": "N1", "text": "Now look at Part 4. Look at questions 31 to 36."},
                {"speaker": "PAUSE", "text": "[PAUSE:40]"},
                {"speaker": "N1", "text": "Now listen carefully and answer questions 31 to 36."},
                {
                    "speaker": "S1",
                    "text": (
                        "Each participant wore an actigraphy device for fourteen days and "
                        "completed a sleep diary. Morning light and caffeine drink timing "
                        f"mattered. {_pad(180)}"
                    ),
                },
                {"speaker": "N1", "text": "Before you hear the rest, look at questions 37 to 40."},
                {"speaker": "PAUSE", "text": "[PAUSE:25]"},
                {"speaker": "N1", "text": "Now listen and answer questions 37 to 40."},
                {
                    "speaker": "S1",
                    "text": (
                        "Sleep regularity used the midpoint of sleep. Short naps under twenty "
                        "minutes were mild; late afternoon naps were worse. Quiet wakefulness "
                        f"can look like sleep. More longitudinal studies across age groups "
                        f"are needed. {_pad(180)}"
                    ),
                },
                {
                    "speaker": "N1",
                    "text": "That is the end of Part 4. You now have one minute to check.",
                },
                {"speaker": "PAUSE", "text": "[PAUSE:60]"},
            ]
        },
        "parts": [
            {
                "partNumber": 4,
                "questionGroups": [
                    {
                        "groupRange": "31-40",
                        "type": "note_completion",
                        "title": "Sleep research",
                        "subInstructions": "Write ONE WORD ONLY.",
                        "notesOutline": outline,
                        "questions": [
                            {"number": i, "type": "note_completion", "notes": f"gap {i}"}
                            for i in range(31, 41)
                        ],
                    }
                ],
            }
        ],
        "answer_key": {
            "31": "actigraphy",
            "32": "fourteen",
            "33": "morning",
            "34": "caffeine",
            "35": "midpoint",
            "36": "twenty",
            "37": "afternoon",
            "38": "wakefulness",
            "39": "longitudinal",
            "40": "age",
        },
    }
    report = evaluate_structure("listening", content, passage_slot=4)
    assert not any(f.code == "L-NOTES-OUTLINE" and f.severity == "must" for f in report.findings)
    assert not any(f.code == "L-NOTES-FILLER" and f.severity == "must" for f in report.findings)


def test_reading_p1_short_passage_must_fail() -> None:
    short = [" ".join(["word"] * 50) for _ in range(8)]  # ~400 words
    content = {
        "type": "reading",
        "sections": [
            {
                "title": "Short passage",
                "passage": short,
                "questionGroups": [
                    {
                        "id": "g1",
                        "instruction": "Choose A, B, C or D.",
                        "type": "multiple_choice",
                        "questions": [
                            {
                                "id": f"q{i}",
                                "type": "multiple_choice",
                                "label": str(i),
                                "question": f"Why does the writer mention topic {i}?",
                                "options": {
                                    "A": "Because it supports the main argument clearly",
                                    "B": "Because it contradicts earlier evidence given",
                                    "C": "Because it is unrelated to the passage topic",
                                    "D": "Because it only appears in the final paragraph",
                                },
                            }
                            for i in range(1, 14)
                        ],
                    }
                ],
            }
        ],
        "answer_key": {str(i): "A" for i in range(1, 14)},
    }
    report = evaluate_structure("reading", content, passage_slot=1)
    assert any(f.code == "R-WC-LOW" and f.severity == "must" for f in report.findings)


def test_reading_mcq_without_options_must_fail() -> None:
    passage = [" ".join(["word"] * 100) for _ in range(9)]  # ~900 words
    content = {
        "type": "reading",
        "sections": [
            {
                "title": "Long enough",
                "passage": passage,
                "questionGroups": [
                    {
                        "id": "mcq",
                        "instruction": "Choose the correct letter, A, B, C or D.",
                        "type": "multiple_choice",
                        "questions": [
                            {
                                "id": "q1",
                                "type": "multiple_choice",
                                "label": "1",
                                "question": "What point does the writer make?",
                            }
                        ],
                    }
                ],
            }
        ],
        "answer_key": {"1": "B"},
    }
    report = evaluate_structure("reading", content, passage_slot=1)
    assert any(f.code == "R-MCQ-OPTS" and f.severity == "must" for f in report.findings)


def test_reading_matching_bank_must_be_larger() -> None:
    passage = [" ".join(["word"] * 100) for _ in range(9)]
    content = {
        "type": "reading",
        "sections": [
            {
                "title": "Features",
                "passage": passage,
                "questionGroups": [
                    {
                        "id": "match",
                        "type": "matching",
                        "instruction": "Match each approach with a characteristic.",
                        "options": {"A": "One", "B": "Two", "C": "Three"},
                        "questions": [
                            {"id": f"q{i}", "type": "matching", "label": str(i), "question": f"Item {i}"}
                            for i in range(1, 4)
                        ],
                    }
                ],
            }
        ],
        "answer_key": {"1": "A", "2": "B", "3": "C"},
    }
    report = evaluate_structure("reading", content, passage_slot=1)
    assert any(f.code == "R-MATCH-BANK" and f.severity == "must" for f in report.findings)
