"""Unit tests for listening Phase-1 script + questions wiring (no LLM)."""

from __future__ import annotations

from typing import Any

import pytest

from app.pipeline import merge_listening_parts
from app.rules.structure import evaluate_structure
from app.schemas.generation import GenerateRequest
from app.skills import load_skill

INTRO = (
    "Welcome to this IELTS-style Listening practice test. You will hear a number of "
    "different recordings, and you will have to answer questions on what you hear. "
    "There will be time for you to read the questions and check your work. All the "
    "recordings will be played once only. The test is in four parts. Now look at Part 1."
)

# ~320 spoken words when combined with intro (~70) + dialogue padding
_DIALOGUE_PAD = (
    "We usually update the notice board every Tuesday morning near the library entrance, "
    "and the community workshop is on Thursday afternoon by the old oak tree. The water "
    "feature in the south section is well maintained, and volunteers can sign up through "
    "the park website or at the main office. There is also a guided walk on Saturday, "
    "a composting clinic next month, and free seedlings for residents who bring their own "
    "containers. Please remember to bring gloves if you join the planting group, and check "
    "the weather forecast before you arrive because outdoor sessions may move indoors when "
    "it rains heavily. The visitor centre opens at nine and closes at five on weekdays."
)


def _ten_questions_two_types(start: int = 1) -> list[dict[str, Any]]:
    mid = start + 4
    end = start + 9
    return [
        {
            "groupRange": f"{start}-{mid}",
            "subInstructions": "Write NO MORE THAN TWO WORDS AND/OR A NUMBER.",
            "questions": [
                {
                    "number": start + i,
                    "type": "note_completion",
                    "prompt": f"Item {start + i}: ……",
                }
                for i in range(5)
            ],
        },
        {
            "groupRange": f"{mid + 1}-{end}",
            "subInstructions": "Choose the correct letter, A, B or C.",
            "questions": [
                {
                    "number": start + 5 + i,
                    "type": "multiple_choice",
                    "prompt": f"Choice {start + 5 + i}?",
                    "options": ["A", "B", "C"],
                }
                for i in range(5)
            ],
        },
    ]


def _part1_ok(**overrides: Any) -> dict[str, Any]:
    long_a = _DIALOGUE_PAD * 2
    long_b = _DIALOGUE_PAD * 2
    content: dict[str, Any] = {
        "type": "listening",
        "partNumber": 1,
        "speakers": [
            {"id": "N1", "role": "narrator", "gender": "female", "accent": "british"},
            {"id": "S1", "role": "clerk", "gender": "female", "accent": "british"},
            {"id": "S2", "role": "customer", "gender": "male", "accent": "british"},
        ],
        "script": {
            "turns": [
                {"speaker": "N1", "text": INTRO + " Look at questions 1 to 6."},
                {"speaker": "PAUSE", "text": "[PAUSE:40]"},
                {
                    "speaker": "N1",
                    "text": "Now listen carefully and answer questions 1 to 6.",
                },
                {
                    "speaker": "S1",
                    "text": (
                        "Good morning. Welcome to Willow Creek Park. The annual fee is "
                        "fifty pounds. " + long_a
                    ),
                },
                {
                    "speaker": "S2",
                    "text": (
                        "Great, I'll take the annual option and join the planting group. "
                        + long_a
                    ),
                },
                {
                    "speaker": "N1",
                    "text": (
                        "Before you hear the rest of the conversation, look at questions 7 to 10."
                    ),
                },
                {"speaker": "PAUSE", "text": "[PAUSE:25]"},
                {
                    "speaker": "N1",
                    "text": "Now listen and answer questions 7 to 10.",
                },
                {
                    "speaker": "S1",
                    "text": (
                        "Parking is free beside the library entrance and the cafe serves "
                        "tea after the workshop. " + long_b
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
        "parts": [{"partNumber": 1, "questionGroups": _ten_questions_two_types(1)}],
        "answer_key": {
            "1": "annual",
            "2": "Tuesday",
            "3": "Thursday",
            "4": "website",
            "5": "gloves",
            "6": "A",
            "7": "B",
            "8": "C",
            "9": "A",
            "10": "B",
        },
        "document": "# Listening Part 1\n\nScript and questions.",
        "format": "markdown",
    }
    content.update(overrides)
    return content


def test_listening_skills_mention_tts_schema() -> None:
    gen = load_skill("listening", "generator").lower()
    assert "script" in gen and "turns" in gen
    assert "speakers" in gen
    assert "narrator" in gen
    assert "welcome" in gen
    assert "exactly 10" in gen or "exactly **10**" in gen
    assert "[pause:40]" in gen or "[pause:30]" in gen
    assert "[pause:60]" in gen
    assert "550" in gen and "750" in gen
    assert "400" in gen  # content-speaker floor
    assert "exam-clock" in gen or "exam clock" in gen
    assert "now listen" in gen
    assert "180" in gen  # half minimum
    ev = load_skill("listening", "evaluator").lower()
    assert "must" in ev and "should" in ev
    assert "exactly **10**" in ev or "exactly 10" in ev
    assert "narrator" in ev


def test_listening_structure_requires_turns_and_speakers() -> None:
    report = evaluate_structure("listening", _part1_ok(), passage_slot=1)
    musts = [f for f in report.findings if f.severity == "must"]
    assert not musts, [f.message for f in musts]
    assert report.passed


def test_listening_part1_rejects_fewer_than_ten_questions() -> None:
    content = _part1_ok()
    content["parts"][0]["questionGroups"] = [
        {
            "groupRange": "1-5",
            "subInstructions": "Write ONE WORD ONLY.",
            "questions": [
                {"number": i, "type": "note_completion", "prompt": f"Q{i}"} for i in range(1, 6)
            ],
        }
    ]
    report = evaluate_structure("listening", content, passage_slot=1)
    assert any(f.code == "L-QC" and f.severity == "must" for f in report.findings)
    assert not report.passed


def test_listening_parts_1_to_3_reject_single_type() -> None:
    content = _part1_ok()
    content["parts"][0]["questionGroups"] = [
        {
            "groupRange": "1-10",
            "subInstructions": "Write ONE WORD ONLY.",
            "questions": [
                {"number": i, "type": "note_completion", "prompt": f"Q{i}"} for i in range(1, 11)
            ],
        }
    ]
    report = evaluate_structure("listening", content, passage_slot=1)
    assert any(f.code == "L-TYPES" and f.severity == "must" for f in report.findings)
    assert "2–3" in next(f.message for f in report.findings if f.code == "L-TYPES")


def test_listening_part4_allows_single_notes_type() -> None:
    content = _part1_ok()
    content["partNumber"] = 4
    content["speakers"] = [
        {"id": "N1", "role": "narrator", "gender": "female", "accent": "british"},
        {"id": "S1", "role": "lecturer", "gender": "female", "accent": "british"},
    ]
    content["parts"] = [
        {
            "partNumber": 4,
            "questionGroups": [
                {
                    "groupRange": "31-40",
                    "subInstructions": "Write NO MORE THAN TWO WORDS AND/OR A NUMBER.",
                    "questions": [
                        {
                            "number": i,
                            "type": "note_completion",
                            "prompt": f"Item {i}: ……",
                        }
                        for i in range(31, 41)
                    ],
                }
            ],
        }
    ]
    content["answer_key"] = {str(i): "erosion" for i in range(31, 41)}
    report = evaluate_structure("listening", content, passage_slot=4)
    assert not any(f.code == "L-TYPES" for f in report.findings)


def test_listening_part4_rejects_two_types() -> None:
    content = _part1_ok()
    content["partNumber"] = 4
    content["speakers"] = [
        {"id": "N1", "role": "narrator", "gender": "female", "accent": "british"},
        {"id": "S1", "role": "lecturer", "gender": "female", "accent": "british"},
    ]
    content["parts"] = [{"partNumber": 4, "questionGroups": _ten_questions_two_types(31)}]
    content["answer_key"] = {str(i): "erosion" for i in range(31, 36)}
    content["answer_key"].update({str(i): "A" for i in range(36, 41)})
    report = evaluate_structure("listening", content, passage_slot=4)
    assert any(f.code == "L-TYPES" and f.severity == "must" for f in report.findings)
    assert "exactly 1" in next(f.message for f in report.findings if f.code == "L-TYPES")


def test_listening_part1_requires_intro_and_enough_words() -> None:
    content = {
        "type": "listening",
        "partNumber": 1,
        "speakers": [
            {"id": "S1", "role": "clerk", "gender": "female", "accent": "british"},
            {"id": "S2", "role": "customer", "gender": "male", "accent": "british"},
        ],
        "script": {
            "turns": [
                {"speaker": "S1", "text": "Good morning. The annual fee is fifty pounds."},
                {"speaker": "S2", "text": "Great, I'll take the annual option."},
            ]
        },
        "parts": [
            {
                "partNumber": 1,
                "questionGroups": [
                    {
                        "groupRange": "1-1",
                        "subInstructions": "Write ONE WORD ONLY.",
                        "questions": [
                            {"number": 1, "type": "note_completion", "prompt": "Fee type: ……"}
                        ],
                    }
                ],
            }
        ],
        "answer_key": {"1": "annual"},
    }
    report = evaluate_structure("listening", content, passage_slot=1)
    codes = {f.code for f in report.findings if f.severity == "must"}
    assert "L-QC" in codes
    assert "L-WC" in codes
    assert "L-INTRO" in codes or "L-INTRO-SP" in codes
    assert not report.passed


def test_listening_part2_opening_must_name_part() -> None:
    """Topic-only Part 2 open fails; 'Now look at Part 2' passes L-INTRO."""
    pad = _DIALOGUE_PAD * 3
    base_speakers = [
        {"id": "N1", "role": "narrator", "gender": "female", "accent": "british"},
        {"id": "S1", "role": "guide", "gender": "male", "accent": "british"},
    ]
    groups = _ten_questions_two_types(11)

    missing = {
        "type": "listening",
        "partNumber": 2,
        "speakers": base_speakers,
        "script": {
            "turns": [
                {
                    "speaker": "N1",
                    "text": (
                        "You will hear a library manager giving a talk about facilities. "
                        "First, you have some time to look at questions 11 to 16."
                    ),
                },
                {"speaker": "PAUSE", "text": "[PAUSE:40]"},
                {"speaker": "N1", "text": "Now listen carefully and answer questions 11 to 16."},
                {"speaker": "S1", "text": "Good morning everyone. Welcome to the library. " + pad},
                {
                    "speaker": "N1",
                    "text": "Before you hear the rest of the talk, look at questions 17 to 20.",
                },
                {"speaker": "PAUSE", "text": "[PAUSE:25]"},
                {"speaker": "N1", "text": "Now listen and answer questions 17 to 20."},
                {
                    "speaker": "S1",
                    "text": "Next I will describe four workshops including option A. " + pad,
                },
                {
                    "speaker": "N1",
                    "text": (
                        "That is the end of Part 2. You now have one minute to check your "
                        "answers to Part 2."
                    ),
                },
                {"speaker": "PAUSE", "text": "[PAUSE:60]"},
            ]
        },
        "parts": [{"partNumber": 2, "questionGroups": groups}],
        "answer_key": {
            **{str(i): "library" for i in range(11, 16)},
            **{str(i): "A" for i in range(16, 21)},
        },
    }
    report = evaluate_structure("listening", missing, passage_slot=2)
    assert any(
        f.code == "L-INTRO" and f.severity == "must" and "name this part" in f.message.lower()
        for f in report.findings
    )

    ok = {
        **missing,
        "script": {
            "turns": [
                {
                    "speaker": "N1",
                    "text": (
                        "Now look at Part 2. You will hear a library manager giving a talk "
                        "about facilities. First, you have some time to look at questions 11 to 16."
                    ),
                },
                *missing["script"]["turns"][1:],
            ]
        },
    }
    report_ok = evaluate_structure("listening", ok, passage_slot=2)
    assert not any(
        f.code == "L-INTRO" and "name this part" in f.message.lower() for f in report_ok.findings
    )


def test_listening_part2_rejects_two_speakers() -> None:
    content = {
        "type": "listening",
        "partNumber": 2,
        "speakers": [
            {"id": "N1", "role": "narrator", "gender": "female", "accent": "american"},
            {"id": "S1", "role": "guide", "gender": "female", "accent": "american"},
            {"id": "S2", "role": "extra", "gender": "male", "accent": "american"},
        ],
        "script": {
            "turns": [
                {"speaker": "N1", "text": "Part 2. Look at questions 11 to 15."},
                {"speaker": "PAUSE", "text": "[PAUSE:40]"},
                {"speaker": "S1", "text": "Welcome to the museum tour today. " + _DIALOGUE_PAD * 3},
            ]
        },
        "parts": [{"partNumber": 2, "questionGroups": _ten_questions_two_types(11)}],
        "answer_key": {str(i): "museum" for i in range(11, 21)},
    }
    # Fix answer key tokens to appear in script
    content["answer_key"] = {str(i): "museum" for i in range(11, 16)}
    content["answer_key"].update({str(i): "A" for i in range(16, 21)})
    content["script"]["turns"][2]["text"] = (
        "Welcome to the museum tour today. Choose option A when unsure. " + _DIALOGUE_PAD * 3
    )
    report = evaluate_structure("listening", content, passage_slot=2)
    assert any(f.code == "L-SP-CNT" for f in report.findings)


def test_listening_map_requires_visual_brief() -> None:
    content = {
        "type": "listening",
        "speakers": [
            {"id": "N1", "role": "narrator", "gender": "female", "accent": "british"},
            {"id": "S1", "role": "guide", "gender": "female", "accent": "british"},
        ],
        "script": {
            "turns": [
                {"speaker": "N1", "text": "Part 2. Look at questions 11 to 20."},
                {"speaker": "PAUSE", "text": "[PAUSE:40]"},
                {"speaker": "S1", "text": "The cafe is next to the library. " + _DIALOGUE_PAD * 3},
            ]
        },
        "parts": [
            {
                "partNumber": 2,
                "questionGroups": [
                    {
                        "groupRange": "11-20",
                        "type": "map_labelling",
                        "subInstructions": "Label the map.",
                        "questions": [
                            {
                                "number": i,
                                "type": "map_labelling",
                                "prompt": (
                                    "cafe"
                                    if i == 11
                                    else "library"
                                    if i == 12
                                    else f"feature {i}"
                                ),
                            }
                            for i in range(11, 21)
                        ],
                        "options": ["A", "B", "C", "D", "E", "F", "G"],
                    }
                ],
            }
        ],
        "answer_key": {str(i): "cafe" for i in range(11, 21)},
    }
    report = evaluate_structure("listening", content, passage_slot=2)
    assert any(f.code == "L-MAP-BRIEF" and f.severity == "must" for f in report.findings)
    assert not any(
        f.code == "L-MAP" and "not supported" in f.message.lower() for f in report.findings
    )
    assert any(f.code == "L-MAP-LABEL" and f.severity == "must" for f in report.findings) is False


def test_listening_map_stub_stems_fail_label_rule() -> None:
    from app.rules.structure import evaluate_structure

    content = {
        "type": "listening",
        "partNumber": 2,
        "speakers": [
            {"id": "N1", "role": "narrator", "gender": "female", "accent": "british"},
            {"id": "S1", "role": "guide", "gender": "female", "accent": "british"},
        ],
        "script": {
            "turns": [
                {"speaker": "N1", "text": "Part 2. Look at questions 11 to 20."},
                {"speaker": "PAUSE", "text": "[PAUSE:40]"},
                {"speaker": "S1", "text": "The cafe is next to the library. " + _DIALOGUE_PAD * 3},
            ]
        },
        "parts": [
            {
                "partNumber": 2,
                "questionGroups": [
                    {
                        "groupRange": "11-20",
                        "type": "map_labelling",
                        "subInstructions": "Label the map.",
                        "visual": {
                            "kind": "plan",
                            "scenario": "A simple site plan with cafe and library marked for visitors.",
                            "layout": [{"id": "11", "position": "west"}],
                            "features": ["cafe", "library"],
                        },
                        "questions": [
                            {
                                "number": i,
                                "type": "map_labelling",
                                "question": f"Label the plan. Write the correct answer for blank {i}.",
                            }
                            for i in range(11, 21)
                        ],
                    }
                ],
            }
        ],
        "answer_key": {str(i): "cafe" for i in range(11, 21)},
    }
    report = evaluate_structure("listening", content, passage_slot=2)
    assert any(f.code == "L-MAP-LABEL" and f.severity == "must" for f in report.findings)

def test_listening_map_with_visual_brief_allows_empty_images() -> None:
    from app.content.listening_brief import extract_listening_visual_briefs
    from app.content.listening_normalize import normalize_listening_content

    content = {
        "type": "listening",
        "partNumber": 2,
        "speakers": [
            {"id": "N1", "role": "narrator", "gender": "female", "accent": "british"},
            {"id": "S1", "role": "guide", "gender": "female", "accent": "british"},
        ],
        "script": {
            "turns": [
                {
                    "speaker": "N1",
                    "text": "Now look at Part 2. You will hear a guide. "
                    "First look at questions 11 to 16.",
                },
                {"speaker": "PAUSE", "text": "[PAUSE:40]"},
                {"speaker": "N1", "text": "Now listen and answer questions 11 to 16."},
                {
                    "speaker": "S1",
                    "text": (
                        "Welcome. As you enter, the cafe is on your left and the library "
                        "is straight ahead past the stairs. " + _DIALOGUE_PAD * 8
                    ),
                },
                {
                    "speaker": "N1",
                    "text": "Before you hear the rest, look at questions 17 to 20.",
                },
                {"speaker": "PAUSE", "text": "[PAUSE:25]"},
                {"speaker": "N1", "text": "Now listen and answer questions 17 to 20."},
                {
                    "speaker": "S1",
                    "text": (
                        "Opposite the cafe you will find the gift shop, then the exit "
                        "on the east side. " + _DIALOGUE_PAD * 8
                    ),
                },
                {
                    "speaker": "N1",
                    "text": "That is the end of Part 2. You now have one minute to check.",
                },
                {"speaker": "PAUSE", "text": "[PAUSE:60]"},
            ]
        },
        "parts": [
            {
                "partNumber": 2,
                "questionGroups": [
                    {
                        "groupRange": "11-16",
                        "type": "map_labelling",
                        "subInstructions": "Label the plan. Write NO MORE THAN TWO WORDS.",
                        "visual": {
                            "kind": "plan",
                            "scenario": (
                                "Ground floor of a community centre. Visitors enter from "
                                "the south; blanks mark cafe, library, stairs area."
                            ),
                            "orientation": "north at top; entrance south",
                            "layout": [
                                {"id": "11", "position": "west of entrance", "answer": "cafe"},
                                {
                                    "id": "12",
                                    "position": "north of entrance",
                                    "answer": "library",
                                },
                            ],
                            "features": ["entrance", "stairs", "cafe", "library"],
                            "must_show": ["entrance", "stairs", "north arrow"],
                            "must_not_show": ["printed answers on blanks"],
                        },
                        "images": [],
                        "options": ["A", "B", "C", "D", "E", "F", "G", "H"],
                        "questions": [
                            {
                                "number": i,
                                "type": "map_labelling",
                                "prompt": {
                                    11: "cafe",
                                    12: "library",
                                    13: "stairs",
                                    14: "gift shop",
                                    15: "ticket desk",
                                    16: "main exit",
                                }[i],
                            }
                            for i in range(11, 17)
                        ],
                    },
                    {
                        "groupRange": "17-20",
                        "type": "multiple_choice",
                        "subInstructions": "Choose the correct letter, A, B or C.",
                        "questions": [
                            {
                                "number": i,
                                "type": "multiple_choice",
                                "prompt": f"Q{i}",
                                "options": {"A": "x", "B": "y", "C": "z"},
                            }
                            for i in range(17, 21)
                        ],
                    },
                ],
            }
        ],
        "answer_key": {
            **{str(i): "cafe" for i in range(11, 14)},
            **{str(i): "library" for i in range(14, 17)},
            **{str(i): "A" for i in range(17, 21)},
        },
    }
    normalize_listening_content(content)
    report = evaluate_structure("listening", content, passage_slot=2)
    assert not any(f.code == "L-MAP-BRIEF" and f.severity == "must" for f in report.findings)
    assert any(f.code == "L-MAP-IMG" and f.severity == "info" for f in report.findings)
    assert content["parts"][0]["questionGroups"][0].get("image_status") == "pending_vendor"

    briefs = extract_listening_visual_briefs(content)
    assert len(briefs) == 1
    assert briefs[0]["visual"]["kind"] == "plan"
    assert briefs[0]["images"] == []
    assert briefs[0]["image_status"] == "pending_vendor"
    assert briefs[0]["audio_cue"]["script_turns"]


def test_merge_listening_parts_prefixes_speakers() -> None:
    parts = [
        {
            "type": "listening",
            "speakers": [{"id": "S1", "role": "a", "gender": "female", "accent": "british"}],
            "script": {"turns": [{"speaker": "S1", "text": "Hello annual plan"}]},
            "parts": [{"partNumber": 1, "questionGroups": []}],
            "answer_key": {"1": "annual"},
            "document": "Part one doc",
        },
        {
            "type": "listening",
            "speakers": [{"id": "S1", "role": "guide", "gender": "male", "accent": "american"}],
            "script": {"turns": [{"speaker": "S1", "text": "Welcome library tour"}]},
            "parts": [{"partNumber": 2, "questionGroups": []}],
            "answer_key": {"11": "library"},
            "document": "Part two doc",
        },
    ]
    merged = merge_listening_parts(parts)
    assert merged["type"] == "listening"
    assert merged["parts_linked"] == 2
    ids = {s["id"] for s in merged["speakers"]}
    assert "P1_S1" in ids and "P2_S1" in ids
    assert merged["script"]["turns"][0]["speaker"] == "P1_S1"
    assert merged["script"]["turns"][1]["speaker"] == "P2_S1"
    assert merged["answer_key"]["1"] == "annual"
    assert "Listening Part 1" in merged["document"]


def test_merge_listening_keeps_pause_speaker() -> None:
    parts = [
        {
            "type": "listening",
            "speakers": [{"id": "S1", "role": "a", "gender": "female", "accent": "british"}],
            "script": {
                "turns": [
                    {"speaker": "PAUSE", "text": "[PAUSE:30]"},
                    {"speaker": "S1", "text": "Hello annual plan"},
                ]
            },
            "parts": [{"partNumber": 1, "questionGroups": []}],
            "answer_key": {"1": "annual"},
        },
        {
            "type": "listening",
            "speakers": [{"id": "S1", "role": "guide", "gender": "male", "accent": "american"}],
            "script": {
                "turns": [
                    {"speaker": "PAUSE", "text": "[PAUSE:30]"},
                    {"speaker": "S1", "text": "Welcome library tour"},
                ]
            },
            "parts": [{"partNumber": 2, "questionGroups": []}],
            "answer_key": {"11": "library"},
        },
    ]
    merged = merge_listening_parts(parts)
    speakers = [t["speaker"] for t in merged["script"]["turns"]]
    assert speakers == ["PAUSE", "P1_S1", "PAUSE", "P2_S1"]


def test_listening_total_parts_sync() -> None:
    req = GenerateRequest(module="listening", topic="museums", part_count=3)
    assert req.total_parts == 3


def test_listening_part4_needs_exam_clock_not_bare_opening_pause() -> None:
    content = {
        "type": "listening",
        "partNumber": 4,
        "speakers": [
            {"id": "N1", "role": "narrator", "gender": "female", "accent": "british"},
            {"id": "S1", "role": "lecturer", "gender": "female", "accent": "british"},
        ],
        "script": {
            "turns": [
                {"speaker": "PAUSE", "text": "[PAUSE:30]"},
                {
                    "speaker": "S1",
                    "text": "Today we will discuss glacial erosion in alpine valleys. "
                    + _DIALOGUE_PAD * 6,
                },
            ]
        },
        "parts": [{"partNumber": 4, "questionGroups": _ten_questions_two_types(31)}],
        "answer_key": {str(i): "erosion" for i in range(31, 36)},
    }
    content["answer_key"].update({str(i): "A" for i in range(36, 41)})
    content["script"]["turns"][1]["text"] += " Option A is correct in several cases."
    report = evaluate_structure("listening", content, passage_slot=4)
    codes = {f.code for f in report.findings if f.severity == "must"}
    assert "L-INTRO" in codes or "L-PAUSE-END" in codes or "L-PAUSE-OPEN" in codes


def test_listening_markdown_only_fails_structure() -> None:
    content = {
        "format": "markdown",
        "type": "document",
        "document": "# IELTS Listening Practice Test - Part 1\n\n"
        + "Speaker 1 (S1): Good morning, Kate.\n\n"
        + "Kate (S2): Hi there, Tom.\n",
    }
    report = evaluate_structure("listening", content, passage_slot=1)
    codes = {f.code for f in report.findings if f.severity == "must"}
    assert "L-SCR" in codes
    assert "L-PARTS" in codes
    assert not report.passed


def test_script_only_tts_export_does_not_block_on_l_parts() -> None:
    """Admin Download TTS JSON strips parts[]; Kokoro must still accept the script."""
    from app.rules.structure import tts_blocking_findings

    full = _part1_ok()
    script_only = {
        "type": "listening",
        "partNumber": 1,
        "speakers": full["speakers"],
        "script": full["script"],
    }
    paper_codes = {
        f.code
        for f in evaluate_structure("listening", script_only, passage_slot=1).findings
        if f.severity == "must"
    }
    assert "L-PARTS" in paper_codes

    blockers = tts_blocking_findings(script_only, passage_slot=1)
    assert not any(f.code == "L-PARTS" for f in blockers)
    assert blockers == []


def test_listening_prompt_requires_json_turns() -> None:
    from app.agents.generator import _user_prompt

    text = _user_prompt(
        GenerateRequest(module="listening", topic="urban parks"),
        revision_notes=None,
    )
    assert "JSON is required" in text or "Output ONLY JSON" in text
    assert "script.turns" in text
    assert "exact JSON is NOT required" not in text
    assert "exam instructor" in text.lower() or "look at / review" in text.lower()


def test_pause_inside_dialogue_fails_n1_rule() -> None:
    content = _part1_ok()
    turns = content["script"]["turns"]
    # After look → pause → now-listen → S1, insert a pause before S2
    s1_idx = next(i for i, t in enumerate(turns) if t.get("speaker") == "S1")
    content["script"]["turns"] = [
        *turns[: s1_idx + 1],
        {"speaker": "PAUSE", "text": "[PAUSE:25]"},
        *turns[s1_idx + 1 :],
    ]
    report = evaluate_structure("listening", content, passage_slot=1)
    assert any(f.code == "L-PAUSE-N1" and f.severity == "must" for f in report.findings)
    assert not report.passed


def test_now_listen_must_follow_look_pause_not_precede_it() -> None:
    content = _part1_ok()
    report = evaluate_structure("listening", content, passage_slot=1)
    assert not any(f.code in {"L-LISTEN-PRE", "L-LISTEN-POST"} for f in report.findings)

    bundled = _part1_ok()
    turns = bundled["script"]["turns"]
    turns[0]["text"] = (
        str(turns[0]["text"]) + " Now listen carefully and answer questions 1 to 6."
    )
    bundled["script"]["turns"] = [
        t
        for t in turns
        if not (
            t.get("speaker") == "N1"
            and str(t.get("text") or "").startswith("Now listen carefully")
        )
    ]
    report = evaluate_structure("listening", bundled, passage_slot=1)
    codes = {f.code for f in report.findings if f.severity == "must"}
    assert "L-LISTEN-PRE" in codes
    assert "L-LISTEN-POST" in codes


def test_listening_verbatim_ignores_pause_tags() -> None:
    content = _part1_ok()
    report = evaluate_structure("listening", content, passage_slot=1)
    assert not any(f.code == "L-VER" for f in report.findings)


def test_listening_rejects_n1_padding_without_content_words() -> None:
    """Fat narrator + thin dialogue must fail content-word floor."""
    content = _part1_ok()
    turns = content["script"]["turns"]
    for t in turns:
        if t.get("speaker") in {"S1", "S2"}:
            t["text"] = "Good morning. The fee is fifty pounds and parking is free."
    # Keep answers findable
    content["script"]["turns"][3]["text"] = (
        "Good morning. The annual fee is fifty pounds. Tuesday Thursday website gloves."
    )
    content["script"]["turns"][4]["text"] = "I'll take the annual option near the library."
    content["script"]["turns"][8]["text"] = (
        "Parking is free beside the library entrance and the cafe serves tea."
    )
    report = evaluate_structure("listening", content, passage_slot=1)
    codes = {f.code for f in report.findings if f.severity == "must"}
    assert "L-WC-CONTENT" in codes or "L-WC-HALF" in codes or "L-WC" in codes
    assert not report.passed


def test_listening_rejects_thin_second_half() -> None:
    content = _part1_ok()
    # Keep first half long; gut the second content block
    for t in content["script"]["turns"]:
        if t.get("speaker") == "S1" and "Parking" in str(t.get("text") or ""):
            t["text"] = "Parking is free beside the library entrance."
            break
    report = evaluate_structure("listening", content, passage_slot=1)
    assert any(f.code == "L-WC-HALF" and f.severity == "must" for f in report.findings)
    assert not report.passed


def test_listening_stamps_length_meta() -> None:
    from app.rules.structure import listening_script_stats, stamp_listening_length_meta

    content = _part1_ok()
    stamp_listening_length_meta(content, passage_slot=1)
    assert content["word_count"] >= 550
    assert content["content_word_count"] >= 400
    assert content["pause_seconds_total"] >= 100
    assert content["estimated_duration_seconds"] >= 330
    stats = listening_script_stats(content, passage_slot=1)
    assert stats["half_content_words"] is not None
    first, second = stats["half_content_words"]
    assert first >= 180 and second >= 180


def test_synthesize_rejects_short_script_before_kokoro() -> None:
    from app.tts.kokoro_synth import ScriptValidationError, synthesize_wav_bytes

    paper = {
        "type": "listening",
        "partNumber": 1,
        "speakers": [
            {"id": "N1", "role": "narrator", "gender": "female", "accent": "british"},
            {"id": "S1", "role": "clerk", "gender": "female", "accent": "british"},
        ],
        "script": {
            "turns": [
                {"speaker": "N1", "text": "Look at questions 1 to 5."},
                {"speaker": "PAUSE", "text": "[PAUSE:40]"},
                {"speaker": "S1", "text": "Hello. The cafe is open."},
            ]
        },
        "parts": [{"partNumber": 1, "questionGroups": _ten_questions_two_types(1)}],
        "answer_key": {str(i): "cafe" for i in range(1, 11)},
    }
    with pytest.raises(ScriptValidationError, match="pause|Content-speaker|Spoken words|Estimated"):
        synthesize_wav_bytes(paper)
