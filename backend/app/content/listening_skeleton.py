"""Ensure Listening exam-clock N1 + pause skeleton around content dialogue."""

from __future__ import annotations

import re
from typing import Any

_PAUSE_RE = re.compile(r"\[PAUSE:(\d+(?:\.\d+)?)\]", re.IGNORECASE)


def _is_pause_turn(turn: dict[str, Any]) -> bool:
    sp = str(turn.get("speaker") or "").strip().upper()
    text = str(turn.get("text") or "")
    return sp == "PAUSE" or bool(_PAUSE_RE.search(text))


def _pause_seconds(turn: dict[str, Any]) -> float | None:
    text = str(turn.get("text") or "")
    m = _PAUSE_RE.search(text)
    if m:
        return float(m.group(1))
    if str(turn.get("speaker") or "").upper() == "PAUSE":
        raw = turn.get("seconds") or turn.get("duration")
        try:
            return float(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None
    return None


def _is_narrator(turn: dict[str, Any]) -> bool:
    return str(turn.get("speaker") or "").strip().upper() in {"N1", "NARRATOR", "INSTRUCTOR"}


def _ensure_n1_speaker(speakers: list[Any]) -> list[Any]:
    out = [s for s in speakers if isinstance(s, dict)]
    ids = {str(s.get("id") or "").upper() for s in out}
    if "N1" not in ids:
        out.insert(
            0,
            {
                "id": "N1",
                "role": "instructor",
                "gender": "female",
                "accent": "british",
            },
        )
    return out


def exam_clock_intact(turns: list[Any]) -> bool:
    """True when look→40, mid→25, end→60 pauses exist in order."""
    pauses = [
        _pause_seconds(t)
        for t in turns
        if isinstance(t, dict) and _is_pause_turn(t)
    ]
    pauses = [p for p in pauses if p is not None]
    need = [40.0, 25.0, 60.0]
    # Allow 30 as alternate look-pause
    idx = 0
    for p in pauses:
        target = need[idx]
        if abs(p - target) < 0.5 or (idx == 0 and abs(p - 30.0) < 0.5):
            idx += 1
            if idx >= len(need):
                return True
    return False


def _intro_text(part_number: int, topic: str, q_start: int, q_mid: int) -> str:
    topic_bit = topic.strip() or "the recording"
    if part_number == 1:
        return (
            "Welcome to this Listening practice test. The recordings will be played once only. "
            "The test is in four parts. Now look at Part 1. "
            f"You will hear a conversation about {topic_bit}. "
            f"First you have some time to look at questions {q_start} to {q_mid - 1}."
        )
    return (
        f"Now look at Part {part_number}. "
        f"You will hear a talk about {topic_bit}. "
        f"First you have some time to look at questions {q_start} to {q_mid - 1}."
    )


def apply_listening_exam_skeleton(
    content: dict[str, Any],
    *,
    part_number: int,
    topic: str,
    question_start: int | None = None,
) -> dict[str, Any]:
    """Wrap content turns in a standard N1 + pause exam clock when structure is missing."""
    script = content.get("script")
    if not isinstance(script, dict):
        script = {}
        content["script"] = script
    turns = script.get("turns")
    if not isinstance(turns, list) or not turns:
        return content

    q_start = question_start or (part_number - 1) * 10 + 1
    q_end = q_start + 9
    q_mid = q_start + 5

    if exam_clock_intact(turns):
        # Still ensure opening names the part when Part 2+
        return content

    content_turns = [
        t
        for t in turns
        if isinstance(t, dict) and not _is_pause_turn(t) and not _is_narrator(t)
    ]
    if not content_turns:
        # Keep existing turns but try to append missing end pause
        return content

    mid = max(1, len(content_turns) // 2)
    half1 = content_turns[:mid]
    half2 = content_turns[mid:]

    rebuilt: list[dict[str, Any]] = [
        {"speaker": "N1", "text": _intro_text(part_number, topic, q_start, q_mid)},
        {"speaker": "PAUSE", "text": "[PAUSE:40]"},
        {
            "speaker": "N1",
            "text": f"Now listen carefully and answer questions {q_start} to {q_mid - 1}.",
        },
        *half1,
        {
            "speaker": "N1",
            "text": (
                f"Before you hear the rest of the recording, you have some time to look at "
                f"questions {q_mid} to {q_end}."
            ),
        },
        {"speaker": "PAUSE", "text": "[PAUSE:25]"},
        {
            "speaker": "N1",
            "text": f"Now listen and answer questions {q_mid} to {q_end}.",
        },
        *half2,
        {
            "speaker": "N1",
            "text": (
                f"That is the end of Part {part_number}. "
                "You now have some time to check your answers."
            ),
        },
        {"speaker": "PAUSE", "text": "[PAUSE:60]"},
    ]
    script["turns"] = rebuilt
    content["speakers"] = _ensure_n1_speaker(
        content["speakers"] if isinstance(content.get("speakers"), list) else []
    )
    content["exam_skeleton_applied"] = True
    return content
