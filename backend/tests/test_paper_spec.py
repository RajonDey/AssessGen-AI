"""Unit tests for per-part topics + type_plan paper spec."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.content.paper_spec import (
    default_listening_type_plan,
    default_reading_type_plan,
    resolve_topics,
    resolve_type_plan,
    validate_paper_spec,
)
from app.schemas.generation import GenerateRequest


def test_default_listening_plan_bc_constraints() -> None:
    plan = default_listening_type_plan()
    assert len(plan) == 4
    assert len(plan[3]) == 1
    assert plan[3][0] == "note_completion"
    findings = validate_paper_spec(
        module="listening",
        part_count=4,
        topics=["aa", "bb", "cc", "dd"],
        type_plan=plan,
        topic="hostel",
    )
    assert not [f for f in findings if f.severity == "must"]


def test_listening_part4_rejects_mcq() -> None:
    findings = validate_paper_spec(
        module="listening",
        part_count=4,
        topics=["aa", "bb", "cc", "dd"],
        type_plan=[
            ["form_completion", "note_completion"],
            ["mcq_single", "map_labelling"],
            ["mcq_single", "matching"],
            ["mcq_single"],
        ],
        topic="xx",
    )
    codes = {f.code for f in findings if f.severity == "must"}
    assert "SPEC-L4-NOTES" in codes or "SPEC-L4-ONE-TYPE" in codes


def test_identical_type_sets_rejected() -> None:
    row = ["true_false_notgiven", "sentence_completion"]
    findings = validate_paper_spec(
        module="reading",
        part_count=3,
        topics=["aa", "bb", "cc"],
        type_plan=[row, row, row],
        topic="xx",
    )
    assert any(f.code == "SPEC-TYPEPLAN-DUP" for f in findings)


def test_generate_request_autofills_defaults() -> None:
    req = GenerateRequest(
        module="listening",
        topic="museums",
        part_count=4,
        full_paper=True,
    )
    assert req.topics is not None and len(req.topics) == 4
    assert req.type_plan is not None and len(req.type_plan) == 4
    assert req.type_plan[3] == ["note_completion"]


def test_generate_request_per_part_topics() -> None:
    topics = [
        "hostel booking",
        "park tour",
        "seminar planning",
        "climate lecture",
    ]
    req = GenerateRequest(
        module="listening",
        topic=topics[0],
        topics=topics,
        part_count=4,
    )
    assert req.topic_for_part(1) == "hostel booking"
    assert req.topic_for_part(3) == "seminar planning"
    assert "map_labelling" in req.types_for_part(2)


def test_generate_request_rejects_bad_listening_plan() -> None:
    with pytest.raises(ValidationError):
        GenerateRequest(
            module="listening",
            topic="xx",
            topics=["aa", "bb", "cc", "dd"],
            type_plan=[
                ["form_completion", "note_completion"],
                ["mcq_single", "map_labelling"],
                ["mcq_single", "matching"],
                ["mcq_single", "matching"],
            ],
            part_count=4,
        )


def test_writing_dual_topics_and_kinds() -> None:
    req = GenerateRequest(
        module="writing",
        topic="energy charts",
        part_count=2,
        topic_t1="household energy 2000–2020",
        topic_t2="should cities ban cars",
        task1_kind="line_graph",
        task2_kind="discussion",
    )
    assert req.topic_t1 == "household energy 2000–2020"
    assert req.topic_t2 == "should cities ban cars"
    assert req.task1_kind == "line_graph"
    assert req.task2_kind == "discussion"
    assert req.writing_type == "discussion"


def test_resolve_helpers() -> None:
    topics = resolve_topics(
        module="reading",
        topic="fallback",
        topics=["parks", "bees", "oceans"],
        part_count=3,
    )
    assert topics == ["parks", "bees", "oceans"]
    plan = resolve_type_plan(module="reading", type_plan=None, part_count=3)
    assert plan == default_reading_type_plan()


def test_linked_single_part_keeps_full_plan_length() -> None:
    """part_count=1 with total_parts=4 may carry the full type_plan array."""
    full = default_listening_type_plan()
    req = GenerateRequest(
        module="listening",
        topic="seminar planning",
        topics=[
            "hostel booking",
            "park tour",
            "seminar planning",
            "climate lecture",
        ],
        type_plan=full,
        part_count=1,
        current_part=3,
        total_parts=4,
        listening_section=3,
    )
    assert req.types_for_part(3) == full[2]
    assert req.topic_for_part(3) == "seminar planning"
