"""Normalize Listening generator JSON into the schema rules/TTS expect."""

from __future__ import annotations

from typing import Any


def normalize_listening_content(content: dict[str, Any]) -> dict[str, Any]:
    """In-place-friendly normalize: returns the same dict after fixing common drift."""
    if not isinstance(content, dict):
        return content

    _normalize_answer_key(content)
    _normalize_answer_evidence(content)
    _normalize_question_groups(content)
    return content


def _normalize_answer_key(content: dict[str, Any]) -> None:
    raw = content.get("answer_key")
    if isinstance(raw, dict) and raw:
        # Coerce keys to strings
        content["answer_key"] = {str(k): _scalar_answer(v) for k, v in raw.items()}
        return
    if isinstance(raw, list) and raw:
        content["answer_key"] = {
            str(i): _scalar_answer(v) for i, v in enumerate(raw, start=1)
        }
        return
    # Try to build from questions if key missing
    built = _answers_from_questions(content)
    if built:
        content["answer_key"] = built


def _normalize_answer_evidence(content: dict[str, Any]) -> None:
    raw = content.get("answer_evidence")
    if isinstance(raw, dict) and raw:
        content["answer_evidence"] = {str(k): v for k, v in raw.items()}
        return
    if isinstance(raw, list) and raw:
        content["answer_evidence"] = {str(i): v for i, v in enumerate(raw, start=1)}


def _scalar_answer(value: Any) -> Any:
    if isinstance(value, list):
        return [_scalar_answer(v) for v in value]
    if isinstance(value, dict):
        for key in ("answer", "text", "value", "key"):
            if key in value:
                return _scalar_answer(value[key])
        return str(value)
    return value


def _normalize_question_groups(content: dict[str, Any]) -> None:
    parts = content.get("parts")
    if not isinstance(parts, list):
        return
    for part in parts:
        if not isinstance(part, dict):
            continue
        groups = part.get("questionGroups")
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            questions = group.get("questions")
            if not isinstance(questions, list):
                continue

            # Common drift: group uses "instructions" instead of subInstructions
            if not group.get("subInstructions"):
                for alt in ("instructions", "instruction", "directions", "rubric"):
                    if group.get(alt):
                        group["subInstructions"] = group[alt]
                        break
            if not group.get("subInstructions"):
                for q in questions:
                    if isinstance(q, dict) and q.get("subInstructions"):
                        group["subInstructions"] = q["subInstructions"]
                        break

            group_type = group.get("type") or group.get("questionType") or group.get("item_type")
            if isinstance(group_type, str) and group_type.strip():
                group_type = _normalize_type(group_type)
                group["type"] = group_type
            else:
                group_type = None

            numbers: list[int] = []
            for q in questions:
                if not isinstance(q, dict):
                    continue
                if "number" not in q and q.get("questionNumber") is not None:
                    q["number"] = q["questionNumber"]
                if "prompt" not in q:
                    for alt in ("questionText", "text", "stem"):
                        if q.get(alt):
                            q["prompt"] = q[alt]
                            break
                # Promote group type onto each question when missing (L-TYPES counts question.type)
                q_type = q.get("type") or q.get("questionType") or q.get("item_type") or group_type
                if q_type:
                    q["type"] = _normalize_type(str(q_type))
                num = q.get("number")
                if isinstance(num, int):
                    numbers.append(num)
                elif isinstance(num, str) and num.isdigit():
                    numbers.append(int(num))
            if numbers and not group.get("groupRange"):
                group["groupRange"] = f"{min(numbers)}-{max(numbers)}"

            _ensure_map_visual_slot(group, questions, group_type)


def _ensure_map_visual_slot(
    group: dict[str, Any],
    questions: list[Any],
    group_type: str | None,
) -> None:
    """Empty images[] + pending status for map/plan/diagram vendor handoff."""
    types = [group_type or ""]
    for q in questions:
        if isinstance(q, dict) and q.get("type"):
            types.append(str(q["type"]))
    if not any(_is_map_labelling_type(t) for t in types if t):
        return

    if "images" not in group:
        group["images"] = []
    if not group.get("image_status"):
        group["image_status"] = "attached" if group.get("images") else "pending_vendor"

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
    if isinstance(brief, dict):
        group["visual"] = brief
        group.setdefault("visual_brief", brief)
    elif isinstance(brief, str) and brief.strip():
        wrapped = {"scenario": brief.strip(), "kind": "plan"}
        group["visual"] = wrapped
        group["visual_brief"] = wrapped


def _is_map_labelling_type(qtype: str) -> bool:
    t = qtype.strip().lower().replace("-", "_").replace(" ", "_")
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


def _normalize_type(raw: str) -> str:
    t = raw.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "multiple_choice": "multiple_choice",
        "multiplechoice": "multiple_choice",
        "mcq": "multiple_choice",
        "mcq_single": "multiple_choice",
        "short_answer": "short_answer",
        "shortanswer": "short_answer",
        "note_completion": "note_completion",
        "form_completion": "form_completion",
        "formcompletion": "form_completion",
        "sentence_completion": "sentence_completion",
        "matching": "matching",
        "table_completion": "note_completion",
        "summary_completion": "note_completion",
        "map": "map_labelling",
        "map_label": "map_labelling",
        "map_labeling": "map_labelling",
        "map_labelling": "map_labelling",
        "plan": "map_labelling",
        "plan_label": "map_labelling",
        "plan_labeling": "map_labelling",
        "plan_labelling": "map_labelling",
        "diagram": "map_labelling",
        "diagram_label": "map_labelling",
        "diagram_labeling": "map_labelling",
        "diagram_labelling": "map_labelling",
        "floor_plan": "map_labelling",
        "floorplan": "map_labelling",
    }
    return aliases.get(t, t)


def _answers_from_questions(content: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    parts = content.get("parts")
    if not isinstance(parts, list):
        return out
    for part in parts:
        if not isinstance(part, dict):
            continue
        groups = part.get("questionGroups")
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            for q in group.get("questions") or []:
                if not isinstance(q, dict):
                    continue
                num = q.get("number", q.get("questionNumber"))
                ans = q.get("answer", q.get("correct", q.get("key")))
                if num is None or ans is None:
                    continue
                out[str(num)] = _scalar_answer(ans)
    return out
