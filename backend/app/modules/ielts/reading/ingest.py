"""Deterministic passage ingest for licensed source text (Mode B — ingested)."""

from __future__ import annotations

import re

from app.modules.ielts.reading.schemas import LabelledParagraph, ReadingPassage

_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def ingest_source_text(source_text: str, *, title: str) -> ReadingPassage:
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", source_text.strip()) if chunk.strip()]
    if not chunks:
        msg = "Source text is empty after trimming"
        raise ValueError(msg)
    if len(chunks) > len(_LABELS):
        msg = f"Source text has {len(chunks)} paragraphs; maximum is {len(_LABELS)}"
        raise ValueError(msg)

    paragraphs = [
        LabelledParagraph(label=_LABELS[index], text=text) for index, text in enumerate(chunks)
    ]
    return ReadingPassage(title=title, paragraphs=paragraphs)
