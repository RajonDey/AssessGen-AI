"""Detect unusable (empty) generator output before review/revise loops."""

from __future__ import annotations

from typing import Any

from app.schemas.generation import ReviewFinding

EMPTY_DOCUMENT_MARKER = "(empty model output)"


def _document_text(content: dict[str, Any]) -> str:
    return str(content.get("document") or "").strip()


def has_structured_paper_fields(content: dict[str, Any]) -> bool:
    """True when JSON-like paper fields exist (not a bare placeholder document)."""
    script = content.get("script")
    if isinstance(script, dict) and isinstance(script.get("turns"), list) and script["turns"]:
        return True
    sections = content.get("sections")
    if isinstance(sections, list) and sections:
        return True
    parts = content.get("parts")
    if isinstance(parts, list) and parts:
        return True
    if content.get("type") in {"listening", "reading", "writing"} and (
        content.get("answer_key") or content.get("items") or content.get("prompt")
    ):
        return True
    return False


def is_usable_generated_content(content: dict[str, Any], *, module: str) -> bool:
    """Return False for empty placeholders or document-only stubs with no paper body."""
    doc = _document_text(content)
    if doc == EMPTY_DOCUMENT_MARKER or not doc and not has_structured_paper_fields(content):
        return False

    if module == "listening":
        script = content.get("script")
        return (
            isinstance(script, dict)
            and isinstance(script.get("turns"), list)
            and bool(script["turns"])
        )

    if module == "reading":
        if has_structured_paper_fields(content):
            return True
        return len(doc) >= 80

    if module == "writing":
        if content.get("prompt") or content.get("tasks"):
            return True
        return len(doc) >= 80

    if has_structured_paper_fields(content):
        return True
    return len(doc) >= 40


def empty_content_finding(*, model: str) -> ReviewFinding:
    return ReviewFinding(
        severity="must",
        message=(
            f"Generator ({model}) returned empty or unusable output. "
            "Listening needs a larger local model (e.g. gemma4:12b) — gemma4:e2b often returns blank."
        ),
        code="GEN-EMPTY",
    )
