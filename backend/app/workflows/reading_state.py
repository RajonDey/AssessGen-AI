"""Reading graph shared state."""

from __future__ import annotations

from typing import Any, TypedDict


class ReadingGraphState(TypedDict, total=False):
    run_id: str
    organization_id: str
    status: str
    error: str | None

    topic: str
    target_band: float
    passage_count: int
    question_count: int
    source_mode: str
    source_text: str | None
    license_label: str | None
    adaptation_level: str

    plan: dict[str, Any]
    plan_valid: bool
    planner_attempt: int

    passage: dict[str, Any]
    items: list[dict[str, Any]]
    passage_attempt: int
    revision_attempt: int

    passage_quality: dict[str, Any]
    originality_report: dict[str, Any]
    dedup_report: dict[str, Any]
    item_quality: dict[str, Any]
    critic_output: dict[str, Any]
    human_review: dict[str, Any]

    passage_id: str
    passage_version_id: str
    item_version_ids: list[str]

    invocation_count: int
