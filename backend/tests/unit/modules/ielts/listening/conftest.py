"""Shared test helpers for Listening rules."""

from __future__ import annotations

from app.modules.ielts.listening.context import ScriptRuleContext
from app.modules.ielts.listening.schemas import ListeningScript, ListeningSpeaker, ListeningTurn


def make_script(
    *,
    section: int = 1,
    turns: list[tuple[str, str]] | None = None,
    context: str = "Gym enquiry",
) -> ListeningScript:
    if turns is None:
        turns = [
            ("S1", "Good morning. How can I help?"),
            ("S2", "Hi, I'm looking for membership — um, what's the fee?"),
        ]
    if section == 2:
        speakers = [ListeningSpeaker(id="S1", role="guide")]
    else:
        speakers = [
            ListeningSpeaker(id="S1", role="receptionist"),
            ListeningSpeaker(id="S2", role="customer"),
        ]
    offset = 0
    turn_models: list[ListeningTurn] = []
    for index, (speaker, text) in enumerate(turns):
        start = offset
        end = start + len(text)
        turn_models.append(
            ListeningTurn(speaker=speaker, text=text, start_char=start, end_char=end)
        )
        offset = end + (1 if index < len(turns) - 1 else 0)
    return ListeningScript(
        section=section,
        context=context,
        speakers=speakers,
        turns=turn_models,
    )


def make_script_context(
    script: ListeningScript,
    *,
    target_band: float = 7.0,
) -> ScriptRuleContext:
    return ScriptRuleContext(
        script=script,
        section=script.section,
        target_band=target_band,
    )
