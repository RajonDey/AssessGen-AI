"""Listening schema tests."""

from app.modules.ielts.listening.schemas import ListeningScript, ListeningSpeaker, ListeningTurn


def test_listening_script_transcript() -> None:
    script = ListeningScript(
        section=1,
        context="Gym enquiry",
        speakers=[
            ListeningSpeaker(id="S1", role="receptionist"),
            ListeningSpeaker(id="S2", role="customer"),
        ],
        turns=[
            ListeningTurn(speaker="S1", text="Good morning.", start_char=0, end_char=13),
            ListeningTurn(speaker="S2", text="Hello there.", start_char=14, end_char=26),
        ],
    )
    assert "S1:" in script.transcript
    assert "Good morning" in script.transcript
