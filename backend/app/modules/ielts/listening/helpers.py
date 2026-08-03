"""Shared helpers for IELTS Listening generation and rules."""

from __future__ import annotations

from app.modules.ielts.listening.schemas import ListeningScript, ListeningTurn
from app.modules.ielts.reading.schemas import LabelledParagraph, ReadingPassage


def normalize_turn_offsets(script: ListeningScript) -> ListeningScript:
    """Assign monotonic character offsets into the flat transcript string."""
    offset = 0
    turns: list[ListeningTurn] = []
    for index, turn in enumerate(script.turns):
        start = offset
        end = start + len(turn.text)
        turns.append(
            ListeningTurn(
                speaker=turn.speaker,
                text=turn.text,
                start_char=start,
                end_char=end,
            )
        )
        offset = end + (1 if index < len(script.turns) - 1 else 0)
    return script.model_copy(update={"turns": turns})


def script_to_passage(script: ListeningScript) -> ReadingPassage:
    """Map a listening script to a ReadingPassage for shared item generators/rules."""
    normalized = normalize_turn_offsets(script)
    return ReadingPassage(
        title=normalized.context,
        paragraphs=[LabelledParagraph(label="A", text=normalized.transcript)],
    )


def speaker_ids(script: ListeningScript) -> set[str]:
    return {speaker.id for speaker in script.speakers}
