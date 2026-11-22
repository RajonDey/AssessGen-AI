"""Extract Listening map/plan/diagram visual briefs for external image vendors."""

from __future__ import annotations

from typing import Any


def _is_map_type(raw: str | None) -> bool:
    t = str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not t:
        return False
    if t in {
        "map_labelling",
        "map_labeling",
        "map_label",
        "plan_labelling",
        "plan_labeling",
        "plan_label",
        "diagram_labelling",
        "diagram_labeling",
        "diagram_label",
        "map",
        "plan",
        "diagram",
    }:
        return True
    return ("map" in t or "diagram" in t or t.startswith("plan_")) and "label" in t


def extract_listening_visual_briefs(content: dict[str, Any]) -> list[dict[str, Any]]:
    """Return vendor-ready packs: scenario, layout, script cues, empty images slot."""
    out: list[dict[str, Any]] = []
    parts = content.get("parts")
    if not isinstance(parts, list):
        return out

    answer_key = content.get("answer_key") if isinstance(content.get("answer_key"), dict) else {}
    evidence = (
        content.get("answer_evidence")
        if isinstance(content.get("answer_evidence"), dict)
        else {}
    )
    script_turns = []
    script = content.get("script")
    if isinstance(script, dict) and isinstance(script.get("turns"), list):
        script_turns = [
            {"speaker": t.get("speaker"), "text": t.get("text")}
            for t in script["turns"]
            if isinstance(t, dict)
        ]

    for part in parts:
        if not isinstance(part, dict):
            continue
        part_num = part.get("partNumber")
        groups = part.get("questionGroups")
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            questions = group.get("questions") or []
            if not isinstance(questions, list):
                continue
            group_type = str(group.get("type") or "")
            q_types = [
                str(q.get("type") or "")
                for q in questions
                if isinstance(q, dict)
            ]
            if not (_is_map_type(group_type) or any(_is_map_type(t) for t in q_types)):
                continue

            brief = (
                group.get("visual")
                or group.get("visual_brief")
                or group.get("visualBrief")
                or group.get("scenario")
            )
            if brief is None:
                for q in questions:
                    if not isinstance(q, dict):
                        continue
                    brief = (
                        q.get("visual")
                        or q.get("visual_brief")
                        or q.get("visualBrief")
                        or q.get("scenario")
                    )
                    if brief is not None:
                        break

            numbers: list[Any] = []
            for q in questions:
                if isinstance(q, dict) and q.get("number") is not None:
                    numbers.append(q["number"])

            keys = {str(n): answer_key.get(str(n)) for n in numbers if str(n) in answer_key}
            evid = {str(n): evidence.get(str(n)) for n in numbers if str(n) in evidence}

            images = group.get("images")
            if images is None:
                for q in questions:
                    if isinstance(q, dict) and q.get("images") is not None:
                        images = q["images"]
                        break
            if not isinstance(images, list):
                images = []

            item: dict[str, Any] = {
                "partNumber": part_num,
                "groupRange": group.get("groupRange") or group.get("questionRange"),
                "type": group.get("type") or (q_types[0] if q_types else "map_labelling"),
                "subInstructions": group.get("subInstructions") or group.get("instructions"),
                "questions": [
                    {
                        "number": q.get("number"),
                        "prompt": q.get("prompt") or q.get("questionText"),
                        "type": q.get("type") or group.get("type"),
                    }
                    for q in questions
                    if isinstance(q, dict)
                ],
                "answer_key": keys,
                "answer_evidence": evid,
                "images": images,
                "image_status": group.get("image_status")
                or ("attached" if images else "pending_vendor"),
                "audio_cue": {
                    "script_turns": script_turns,
                    "note": (
                        "Synthesize WAV from the part script via /listening/synthesize; "
                        "walk-through order must match visual.layout blanks."
                    ),
                },
            }
            if isinstance(brief, dict):
                item["visual"] = brief
            elif isinstance(brief, str) and brief.strip():
                item["visual"] = {"scenario": brief.strip()}
            else:
                item["visual"] = {
                    "scenario": "",
                    "note": "Missing visual_brief — regenerate or fill before drawing",
                }
            out.append(item)
    return out
