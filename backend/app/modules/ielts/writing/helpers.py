"""Shared helpers for IELTS Writing generation and rules."""

from __future__ import annotations

from app.modules.ielts.reading.schemas import LabelledParagraph, ReadingPassage
from app.modules.ielts.writing.schemas import WritingTask2Prompt


def prompt_to_passage(prompt: WritingTask2Prompt) -> ReadingPassage:
    """Map a Task 2 prompt to a ReadingPassage for originality and dedup checks."""
    body = prompt.prompt.strip()
    return ReadingPassage(
        title=prompt.topic,
        paragraphs=[LabelledParagraph(label="A", text=body)],
    )
