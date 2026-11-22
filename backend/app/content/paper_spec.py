"""Per-part topics + type plans for BC-style Listening / Reading / Writing papers.

Independent topics per part; question types interlock across the paper (not themes).
Writing uses separate Task 1 / Task 2 kinds — no shared item-type pool.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ListeningItemType = Literal[
    "form_completion",
    "note_completion",
    "table_completion",
    "sentence_completion",
    "summary_completion",
    "short_answer",
    "mcq_single",
    "mcq_multi",
    "matching",
    "map_labelling",
]

ReadingItemType = Literal[
    "true_false_notgiven",
    "yes_no_notgiven",
    "sentence_completion",
    "summary_completion",
    "note_completion",
    "short_answer",
    "heading_match",
    "info_match",
    "feature_match",
    "mcq_single",
    "mcq_multi",
]

Task1Kind = Literal[
    "line_graph",
    "bar_chart",
    "pie_chart",
    "table",
    "process",
    "map",
    "mixed",
    "letter_formal",
    "letter_semi_formal",
    "letter_informal",
]

Task2Kind = Literal[
    "opinion",
    "discussion",
    "problem_solution",
    "advantages_disadvantages",
    "two_part",
]

LISTENING_TYPES: frozenset[str] = frozenset(
    {
        "form_completion",
        "note_completion",
        "table_completion",
        "sentence_completion",
        "summary_completion",
        "short_answer",
        "mcq_single",
        "mcq_multi",
        "matching",
        "map_labelling",
    }
)

READING_TYPES: frozenset[str] = frozenset(
    {
        "true_false_notgiven",
        "yes_no_notgiven",
        "sentence_completion",
        "summary_completion",
        "note_completion",
        "short_answer",
        "heading_match",
        "info_match",
        "feature_match",
        "mcq_single",
        "mcq_multi",
    }
)

LISTENING_PART4_TYPES: frozenset[str] = frozenset(
    {"note_completion", "summary_completion", "sentence_completion"}
)

TASK1_KINDS: frozenset[str] = frozenset(
    {
        "line_graph",
        "bar_chart",
        "pie_chart",
        "table",
        "process",
        "map",
        "mixed",
        "letter_formal",
        "letter_semi_formal",
        "letter_informal",
    }
)

TASK2_KINDS: frozenset[str] = frozenset(
    {
        "opinion",
        "discussion",
        "problem_solution",
        "advantages_disadvantages",
        "two_part",
    }
)

# Canonical aliases → paper-spec ids
_TYPE_ALIASES: dict[str, str] = {
    "form": "form_completion",
    "form_completion": "form_completion",
    "notes": "note_completion",
    "note": "note_completion",
    "note_completion": "note_completion",
    "table": "table_completion",
    "table_completion": "table_completion",
    "sentence": "sentence_completion",
    "sentence_completion": "sentence_completion",
    "summary": "summary_completion",
    "summary_completion": "summary_completion",
    "short_answer": "short_answer",
    "short-answer": "short_answer",
    "mcq": "mcq_single",
    "mcq_single": "mcq_single",
    "multiple_choice": "mcq_single",
    "multiple-choice": "mcq_single",
    "mcq_multi": "mcq_multi",
    "choose_two": "mcq_multi",
    "matching": "matching",
    "feature_match": "feature_match",
    "map": "map_labelling",
    "map_labelling": "map_labelling",
    "plan_labelling": "map_labelling",
    "diagram_labelling": "map_labelling",
    "true_false_notgiven": "true_false_notgiven",
    "true-false-not-given": "true_false_notgiven",
    "tfng": "true_false_notgiven",
    "yes_no_notgiven": "yes_no_notgiven",
    "yes-no-not-given": "yes_no_notgiven",
    "ynng": "yes_no_notgiven",
    "heading_match": "heading_match",
    "matching-headings": "heading_match",
    "matching_headings": "heading_match",
    "info_match": "info_match",
    "matching-information": "info_match",
    "feature-match": "feature_match",
    "matching_features": "feature_match",
}


def normalize_item_type(raw: str) -> str:
    key = raw.strip().lower().replace(" ", "_").replace("-", "_")
    # Collapse double underscores from mixed separators
    while "__" in key:
        key = key.replace("__", "_")
    # Try direct + hyphenated original
    if key in _TYPE_ALIASES:
        return _TYPE_ALIASES[key]
    hyphen = raw.strip().lower().replace(" ", "-")
    if hyphen in _TYPE_ALIASES:
        return _TYPE_ALIASES[hyphen]
    underscored = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if underscored in _TYPE_ALIASES:
        return _TYPE_ALIASES[underscored]
    return underscored


def default_listening_type_plan() -> list[list[str]]:
    """BC-typical Listening mix (Parts 1–3: 2 types; Part 4: notes only)."""
    return [
        ["form_completion", "note_completion"],
        ["mcq_single", "map_labelling"],
        ["mcq_single", "matching"],
        ["note_completion"],
    ]


def default_reading_type_plan() -> list[list[str]]:
    """Diversified Academic Reading mix — not a fixed BC matrix."""
    return [
        ["true_false_notgiven", "sentence_completion", "short_answer"],
        ["heading_match", "summary_completion"],
        ["yes_no_notgiven", "mcq_single", "feature_match"],
    ]


def default_task1_kind() -> str:
    return "bar_chart"


def module_part_cap(module: str) -> int:
    return {"reading": 3, "writing": 2, "listening": 4}.get(module, 1)


@dataclass(frozen=True)
class SpecFinding:
    """Lightweight finding — converted to ReviewFinding at the API boundary."""

    severity: Literal["must", "should", "info"]
    message: str
    code: str | None = None


def resolve_topics(
    *,
    module: str,
    topic: str,
    topics: list[str] | None,
    part_count: int,
    topic_t1: str | None = None,
    topic_t2: str | None = None,
) -> list[str]:
    """Return one topic string per part (length == part_count)."""
    n = max(1, min(part_count, module_part_cap(module)))
    primary = topic.strip()

    if module == "writing":
        t1 = (topic_t1 or (topics[0] if topics else None) or primary).strip()
        t2 = (topic_t2 or (topics[1] if topics and len(topics) > 1 else None) or primary).strip()
        if n <= 1:
            return [t1]
        return [t1, t2]

    if topics:
        cleaned = [t.strip() for t in topics if isinstance(t, str) and t.strip()]
        if len(cleaned) >= n:
            return cleaned[:n]
        # Pad short lists with the primary topic (compat); generator still told to stay independent
        while len(cleaned) < n:
            cleaned.append(primary)
        return cleaned[:n]

    return [primary] * n


def resolve_type_plan(
    *,
    module: str,
    type_plan: list[list[str]] | None,
    part_count: int,
) -> list[list[str]]:
    """Return normalized type_plan of length part_count (Writing unused)."""
    n = max(1, min(part_count, module_part_cap(module)))
    if module == "writing":
        return []

    defaults = (
        default_listening_type_plan()
        if module == "listening"
        else default_reading_type_plan()
    )
    if not type_plan:
        return [list(row) for row in defaults[:n]]

    out: list[list[str]] = []
    for i in range(n):
        if i < len(type_plan) and type_plan[i]:
            out.append([normalize_item_type(t) for t in type_plan[i] if str(t).strip()])
        else:
            out.append(list(defaults[i] if i < len(defaults) else defaults[-1]))
    return out


def part_topic(topics: list[str], part_number: int, fallback: str) -> str:
    idx = max(0, part_number - 1)
    if 0 <= idx < len(topics) and topics[idx].strip():
        return topics[idx].strip()
    return fallback.strip()


def part_types(type_plan: list[list[str]], part_number: int) -> list[str]:
    idx = max(0, part_number - 1)
    if 0 <= idx < len(type_plan):
        return list(type_plan[idx])
    return []


def validate_paper_spec(
    *,
    module: str,
    part_count: int,
    topics: list[str] | None,
    type_plan: list[list[str]] | None,
    topic: str,
    topic_t1: str | None = None,
    topic_t2: str | None = None,
    task1_kind: str | None = None,
    task2_kind: str | None = None,
    writing_type: str | None = None,
    listening_section: int = 1,
    total_parts: int | None = None,
    current_part: int = 1,
) -> list[SpecFinding]:
    """L0/L1-style must findings for paper topic + type_plan shape."""
    findings: list[SpecFinding] = []
    n = max(1, min(part_count, module_part_cap(module)))
    # Linked single-part calls keep the full-paper topics/type_plan arrays
    paper_n = max(n, total_parts or n)
    paper_n = min(paper_n, module_part_cap(module))

    def _part_number_for_index(i: int) -> int:
        if module == "listening" and paper_n == 1:
            return max(1, min(4, listening_section))
        if n == 1 and paper_n > 1:
            # Single-row or full-plan under a linked call — prefer current_part for short plans
            if len(type_plan or []) == 1:
                return max(1, min(module_part_cap(module), current_part))
            return i + 1
        return i + 1

    if topics is not None:
        if len(topics) not in {n, paper_n}:
            findings.append(
                SpecFinding(
                    severity="must",
                    code="SPEC-TOPICS-LEN",
                    message=(
                        f"{module} requires topics length {paper_n} "
                        f"(or {n} for a single-part call), got {len(topics)}"
                    ),
                )
            )
        for i, t in enumerate(topics or []):
            if not isinstance(t, str) or len(t.strip()) < 2:
                findings.append(
                    SpecFinding(
                        severity="must",
                        code="SPEC-TOPIC-EMPTY",
                        message=f"topics[{i}] must be a non-empty topic (≥2 chars)",
                    )
                )

    if module == "writing":
        t1k = task1_kind or default_task1_kind()
        t2k = task2_kind or writing_type or "opinion"
        if t1k not in TASK1_KINDS:
            findings.append(
                SpecFinding(
                    severity="must",
                    code="SPEC-TASK1-KIND",
                    message=f"task1_kind '{t1k}' is not a valid Writing Task 1 kind",
                )
            )
        if t2k not in TASK2_KINDS:
            findings.append(
                SpecFinding(
                    severity="must",
                    code="SPEC-TASK2-KIND",
                    message=f"task2_kind '{t2k}' is not a valid Writing Task 2 kind",
                )
            )
        if topic_t1 is not None and len(topic_t1.strip()) < 2:
            findings.append(
                SpecFinding(
                    severity="must",
                    code="SPEC-TOPIC-T1",
                    message="topic_t1 must be ≥2 characters when provided",
                )
            )
        if topic_t2 is not None and len(topic_t2.strip()) < 2:
            findings.append(
                SpecFinding(
                    severity="must",
                    code="SPEC-TOPIC-T2",
                    message="topic_t2 must be ≥2 characters when provided",
                )
            )
        return findings

    if type_plan is not None:
        if len(type_plan) not in {n, paper_n}:
            findings.append(
                SpecFinding(
                    severity="must",
                    code="SPEC-TYPEPLAN-LEN",
                    message=(
                        f"{module} requires type_plan length {paper_n} "
                        f"(or {n} for a single-part call), got {len(type_plan)}"
                    ),
                )
            )
        for i, row in enumerate(type_plan):
            part_num = _part_number_for_index(i)
            if not row:
                findings.append(
                    SpecFinding(
                        severity="must",
                        code="SPEC-TYPEPLAN-EMPTY",
                        message=f"type_plan[{i}] (part {part_num}) must list at least one type",
                    )
                )
                continue
            normalized = [normalize_item_type(t) for t in row]
            findings.extend(
                _validate_part_types(module=module, part_number=part_num, types=normalized)
            )

        # Diversification only when validating a full multi-part plan
        if paper_n >= 2 and len(type_plan) >= paper_n:
            sets = [
                frozenset(normalize_item_type(t) for t in row) for row in type_plan[:paper_n]
            ]
            if all(s == sets[0] for s in sets) and sets[0]:
                findings.append(
                    SpecFinding(
                        severity="must",
                        code="SPEC-TYPEPLAN-DUP",
                        message=(
                            "type_plan must diversify across parts — "
                            "identical type sets on every part are not BC-faithful"
                        ),
                    )
                )

    # Always validate resolved defaults when type_plan omitted (listening part constraints)
    if type_plan is None and module in {"listening", "reading"}:
        if module == "listening" and n == 1:
            full = default_listening_type_plan()
            sec = max(1, min(4, listening_section))
            resolved = [full[sec - 1]]
            part_numbers = [sec]
        else:
            resolved = resolve_type_plan(module=module, type_plan=None, part_count=n)
            part_numbers = list(range(1, n + 1))
        for i, row in enumerate(resolved):
            findings.extend(
                _validate_part_types(
                    module=module, part_number=part_numbers[i], types=row
                )
            )

    if not topic or len(topic.strip()) < 2:
        findings.append(
            SpecFinding(
                severity="must",
                code="SPEC-TOPIC",
                message="topic must be ≥2 characters",
            )
        )

    return findings


def _validate_part_types(
    *,
    module: str,
    part_number: int,
    types: list[str],
) -> list[SpecFinding]:
    findings: list[SpecFinding] = []
    allowed = LISTENING_TYPES if module == "listening" else READING_TYPES

    for t in types:
        if t not in allowed:
            findings.append(
                SpecFinding(
                    severity="must",
                    code="SPEC-TYPE-UNKNOWN",
                    message=(
                        f"Part {part_number}: '{t}' is not an allowed {module} item type"
                    ),
                )
            )

    unique = list(dict.fromkeys(types))
    if module == "listening":
        if part_number == 4:
            if len(unique) != 1:
                findings.append(
                    SpecFinding(
                        severity="must",
                        code="SPEC-L4-ONE-TYPE",
                        message="Listening Part 4 type_plan must be exactly one notes/summary type",
                    )
                )
            elif unique[0] not in LISTENING_PART4_TYPES:
                findings.append(
                    SpecFinding(
                        severity="must",
                        code="SPEC-L4-NOTES",
                        message=(
                            "Listening Part 4 must use note_completion, "
                            "summary_completion, or sentence_completion"
                        ),
                    )
                )
        else:
            if not (2 <= len(unique) <= 3):
                findings.append(
                    SpecFinding(
                        severity="must",
                        code="SPEC-L-TYPE-COUNT",
                        message=(
                            f"Listening Part {part_number} type_plan must have "
                            f"2–3 distinct types (got {len(unique)})"
                        ),
                    )
                )
    elif module == "reading":
        if not (2 <= len(unique) <= 3):
            findings.append(
                SpecFinding(
                    severity="must",
                    code="SPEC-R-TYPE-COUNT",
                    message=(
                        f"Reading Part {part_number} type_plan must have "
                        f"2–3 distinct types (got {len(unique)})"
                    ),
                )
            )

    return findings


def paper_spec_summary(
    *,
    module: str,
    topics: list[str],
    type_plan: list[list[str]],
    task1_kind: str | None = None,
    task2_kind: str | None = None,
) -> dict[str, Any]:
    """Compact dict for session storage / planner context."""
    if module == "writing":
        return {
            "topics": topics,
            "task1_kind": task1_kind or default_task1_kind(),
            "task2_kind": task2_kind or "opinion",
        }
    return {"topics": topics, "type_plan": type_plan}
