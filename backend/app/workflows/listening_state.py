"""Listening graph shared state."""

from __future__ import annotations

from typing import Any, TypedDict


class ListeningGraphState(TypedDict, total=False):
    run_id: str
    organization_id: str
    status: str
    error: str | None

    topic: str
    section: int
    target_band: float
    question_count: int
    accent: str

    plan: dict[str, Any]
    script: dict[str, Any]
    passage: dict[str, Any]
    items: list[dict[str, Any]]
    script_attempt: int

    script_quality: dict[str, Any]
    originality_report: dict[str, Any]
    dedup_report: dict[str, Any]
    item_quality: dict[str, Any]
    human_review: dict[str, Any]

    passage_id: str
    passage_version_id: str
    item_version_ids: list[str]

    invocation_count: int
