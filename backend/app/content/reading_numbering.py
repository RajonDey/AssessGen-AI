"""Continuous Academic Reading question numbering (1–40 across three passages)."""

from __future__ import annotations

import re
from typing import Any

# Prefer 13 + 13 + 14 = 40 (standard Academic layout).
READING_QUESTION_RANGES: dict[int, tuple[int, int]] = {
    1: (1, 13),
    2: (14, 26),
    3: (27, 40),
}


def reading_question_range(part_number: int) -> tuple[int, int]:
    """Inclusive start/end question numbers for a Reading passage slot."""
    if part_number in READING_QUESTION_RANGES:
        return READING_QUESTION_RANGES[part_number]
    # Fallback: 13-wide blocks
    start = (part_number - 1) * 13 + 1
    return start, start + 12


def renumber_reading_document(document: str, *, start_number: int) -> str:
    """Shift question numbers in Markdown so the first item becomes start_number."""
    if not document.strip() or start_number < 1:
        return document

    # Detect the lowest question number currently used in headings / numbered items.
    candidates: list[int] = []
    for match in re.finditer(
        r"(?i)(?:questions?|boxes?)\s+(\d+)\s*[–—-]\s*(\d+)",
        document,
    ):
        candidates.append(int(match.group(1)))
        candidates.append(int(match.group(2)))
    for match in re.finditer(r"(?m)^(\d{1,2})[.)]\s", document):
        candidates.append(int(match.group(1)))
    for match in re.finditer(
        r"(?i)(?:boxes?|question)\s+(\d+)\s*[–—-]\s*(\d+)",
        document,
    ):
        candidates.append(int(match.group(1)))

    if not candidates:
        return document

    old_min = min(candidates)
    delta = start_number - old_min
    if delta == 0:
        return document

    # Ranges first (Questions 1–13, boxes 1-5, etc.)
    text = re.sub(
        r"(?i)((?:questions?|boxes?)\s+)(\d+)(\s*[–—-]\s*)(\d+)",
        lambda m: f"{m.group(1)}{int(m.group(2)) + delta}{m.group(3)}{int(m.group(4)) + delta}",
        document,
    )
    # Leading numbered items: "1. " / "12) "
    text = re.sub(
        r"(?m)^(\d{1,2})([.)]\s)",
        lambda m: f"{int(m.group(1)) + delta}{m.group(2)}",
        text,
    )
    # Answer-key table rows that start with a bare number cell
    text = re.sub(
        r"(?m)^\|\s*(\d{1,2})\s*\|",
        lambda m: f"| {int(m.group(1)) + delta} |",
        text,
    )
    # "**10. __________**" style blanks
    text = re.sub(
        r"\*\*(\d{1,2})\.\s*",
        lambda m: f"**{int(m.group(1)) + delta}. ",
        text,
    )
    return text


def _question_number(q: dict[str, Any]) -> int | None:
    for key in ("number", "questionNumber", "id", "label"):
        raw = q.get(key)
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str):
            digits = re.search(r"\d+", raw)
            if digits:
                return int(digits.group(0))
    return None


def renumber_reading_sections(
    sections: list[Any],
    *,
    start_number: int,
) -> tuple[list[Any], dict[int, int]]:
    """Renumber structured section questions; return sections and old→new map."""
    mapping: dict[int, int] = {}
    next_num = start_number
    out: list[Any] = []
    for section in sections:
        if not isinstance(section, dict):
            out.append(section)
            continue
        cloned = dict(section)
        groups = cloned.get("questionGroups")
        if not isinstance(groups, list):
            out.append(cloned)
            continue
        new_groups: list[Any] = []
        for group in groups:
            if not isinstance(group, dict):
                new_groups.append(group)
                continue
            g = dict(group)
            questions = g.get("questions")
            if isinstance(questions, list):
                new_qs: list[Any] = []
                for q in questions:
                    if not isinstance(q, dict):
                        new_qs.append(q)
                        continue
                    q2 = dict(q)
                    old = _question_number(q2)
                    q2["number"] = next_num
                    if old is not None:
                        mapping[old] = next_num
                    if "questionNumber" in q2:
                        q2["questionNumber"] = next_num
                    if isinstance(q2.get("label"), str) and re.fullmatch(r"\d+", q2["label"].strip()):
                        q2["label"] = str(next_num)
                    if isinstance(q2.get("id"), str) and re.fullmatch(r"\d+", q2["id"].strip()):
                        q2["id"] = str(next_num)
                    next_num += 1
                    new_qs.append(q2)
                g["questions"] = new_qs
                if new_qs:
                    first = _question_number(new_qs[0]) if isinstance(new_qs[0], dict) else None
                    last = _question_number(new_qs[-1]) if isinstance(new_qs[-1], dict) else None
                    if first and last:
                        g["groupRange"] = f"{first}-{last}"
                        if "instruction" in g and isinstance(g["instruction"], str):
                            g["instruction"] = re.sub(
                                r"(?i)questions?\s+\d+\s*[–—-]\s*\d+",
                                f"Questions {first}–{last}",
                                g["instruction"],
                            )
            new_groups.append(g)
        cloned["questionGroups"] = new_groups
        out.append(cloned)
    return out, mapping


def remap_answer_key(key: dict[str, Any], mapping: dict[int, int]) -> dict[str, Any]:
    """Map answer_key keys through old→new question numbers."""
    out: dict[str, Any] = {}
    for raw_k, value in key.items():
        k = str(raw_k)
        # Strip optional S1: prefix from older merges
        if ":" in k:
            k = k.split(":", 1)[1]
        digits = re.search(r"\d+", k)
        if not digits:
            out[str(raw_k)] = value
            continue
        old = int(digits.group(0))
        new = mapping.get(old, old)
        out[str(new)] = value
    return out


def apply_reading_part_numbering(
    part: dict[str, Any],
    *,
    part_number: int,
    start_number: int | None = None,
) -> dict[str, Any]:
    """Normalize one Reading part so its questions start at the Academic range."""
    start, _end = reading_question_range(part_number)
    if start_number is not None:
        start = start_number
    out = dict(part)
    sections = out.get("sections")
    mapping: dict[int, int] = {}
    if isinstance(sections, list) and sections:
        new_sections, mapping = renumber_reading_sections(sections, start_number=start)
        out["sections"] = new_sections
    doc = out.get("document")
    if isinstance(doc, str) and doc.strip():
        out["document"] = renumber_reading_document(doc, start_number=start)
    key = out.get("answer_key") or out.get("answerKey")
    if isinstance(key, dict) and key:
        if mapping:
            out["answer_key"] = remap_answer_key(key, mapping)
        else:
            nums: list[int] = []
            for raw_k in key:
                m = re.search(r"\d+", str(raw_k).split(":")[-1])
                if m:
                    nums.append(int(m.group(0)))
            if nums:
                delta = start - min(nums)
                shifted: dict[str, Any] = {}
                for raw_k, value in key.items():
                    m = re.search(r"\d+", str(raw_k).split(":")[-1])
                    if not m:
                        shifted[str(raw_k)] = value
                        continue
                    shifted[str(int(m.group(0)) + delta)] = value
                out["answer_key"] = shifted
    return out
