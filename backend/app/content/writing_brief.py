"""Extract Writing Task 1 visual brief for external image vendors."""

from __future__ import annotations

from typing import Any


def extract_writing_visual_briefs(content: dict[str, Any]) -> list[dict[str, Any]]:
    """Return vendor-ready briefs from Part 1 / Task 1 questions."""
    out: list[dict[str, Any]] = []
    sections = content.get("sections")
    if not isinstance(sections, list):
        return out
    for section in sections:
        if not isinstance(section, dict):
            continue
        title = str(section.get("title") or "").lower()
        if "part 1" not in title and "task 1" not in title:
            continue
        for q in section.get("questions") or []:
            if not isinstance(q, dict):
                continue
            brief = q.get("visual_brief") or q.get("visualBrief") or q.get("scenario")
            item: dict[str, Any] = {
                "title": q.get("title"),
                "question": q.get("question"),
                "task_type": q.get("task_type") or q.get("taskType"),
                "images": q.get("images") or [],
            }
            if isinstance(brief, dict):
                item["visual_brief"] = brief
            elif isinstance(brief, str) and brief.strip():
                item["visual_brief"] = {"description": brief.strip()}
            elif isinstance(q.get("title"), str):
                item["visual_brief"] = {
                    "description": str(q["title"]),
                    "note": "Derived from title — prefer explicit visual_brief",
                }
            out.append(item)
    return out
