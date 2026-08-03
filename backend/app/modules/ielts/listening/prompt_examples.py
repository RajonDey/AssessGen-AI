"""JSON examples for Listening agent prompts."""

from __future__ import annotations

import json

from app.modules.ielts.listening.schemas import ListeningScript, ListeningSpeaker, ListeningTurn


def script_json_example(*, section: int = 1) -> str:
    if section == 1:
        script = ListeningScript(
            section=1,
            context="A customer enquiring about gym membership",
            speakers=[
                ListeningSpeaker(id="S1", role="receptionist", gender="female", accent="british"),
                ListeningSpeaker(id="S2", role="customer", gender="male", accent="british"),
            ],
            turns=[
                ListeningTurn(
                    speaker="S1",
                    text="Good morning, Fitness First. How can I help?",
                    start_char=0,
                    end_char=44,
                ),
                ListeningTurn(
                    speaker="S2",
                    text="Hi, I'm interested in membership — um, what's the monthly fee?",
                    start_char=45,
                    end_char=108,
                ),
            ],
        )
    else:
        script = ListeningScript(
            section=2,
            context="A guided tour of a local museum",
            speakers=[
                ListeningSpeaker(id="S1", role="guide", gender="female", accent="british"),
            ],
            turns=[
                ListeningTurn(
                    speaker="S1",
                    text=(
                        "Welcome everyone. Today we'll explore the history wing "
                        "on the ground floor."
                    ),
                    start_char=0,
                    end_char=76,
                ),
            ],
        )
    return json.dumps(script.model_dump(mode="json"), indent=2)
