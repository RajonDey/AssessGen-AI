"""Writing graph shared state."""

from __future__ import annotations

from typing import Any, TypedDict


class WritingGraphState(TypedDict, total=False):
    run_id: str
    organization_id: str
    status: str
    error: str | None

    topic: str
    question_type: str
    target_band: float

    task2_prompt: dict[str, Any]
    passage: dict[str, Any]
    prompt_attempt: int

    prompt_quality: dict[str, Any]
    originality_report: dict[str, Any]
    dedup_report: dict[str, Any]
    human_review: dict[str, Any]

    passage_id: str
    passage_version_id: str
    item_version_ids: list[str]

    invocation_count: int
