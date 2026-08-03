"""Shared helpers for IELTS Speaking generation and rules."""

from __future__ import annotations

import json

from app.modules.ielts.reading.schemas import LabelledParagraph, ReadingPassage
from app.modules.ielts.speaking.schemas import SpeakingPart1And2


def content_to_text(content: SpeakingPart1And2) -> str:
    """Flatten Part 1 + Part 2 for originality and dedup checks."""
    lines: list[str] = []
    for index, topic in enumerate(content.part1_topics, start=1):
        lines.append(f"Part 1 Topic {index}: {topic.name}")
        lines.extend(f"- {question}" for question in topic.questions)
    part2 = content.part2
    lines.append(f"Part 2: {part2.topic}")
    lines.extend(f"- {bullet}" for bullet in part2.bullets)
    lines.append(part2.explain_prompt)
    return "\n".join(lines)


def content_to_passage(content: SpeakingPart1And2) -> ReadingPassage:
    body = content_to_text(content)
    title = content.part2.topic
    return ReadingPassage(
        title=title,
        paragraphs=[LabelledParagraph(label="A", text=body)],
    )


def content_to_json(content: SpeakingPart1And2) -> dict[str, object]:
    return content.model_dump(mode="json")


def format_content_body(content: SpeakingPart1And2) -> str:
    """Human-readable body stored in passage_versions."""
    return json.dumps(content.model_dump(mode="json"), indent=2)
