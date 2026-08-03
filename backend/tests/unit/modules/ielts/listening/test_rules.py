"""Listening rule tests."""

from app.modules.ielts.listening.rules.r_list_001 import ListeningVerbatimAnswerRule
from app.modules.ielts.listening.rules.r_list_002 import ListeningSpokenRegisterRule
from app.modules.ielts.listening.rules.r_list_004 import ListeningSpeakerLabelRule
from app.modules.ielts.listening.rules.r_list_008 import ListeningSpokenNumbersRule
from tests.unit.modules.ielts.listening.conftest import make_script, make_script_context
from tests.unit.modules.ielts.reading.conftest import make_completion_item, make_item_context


def test_r_list_001_passes_when_answer_in_transcript() -> None:
    item = make_completion_item(answer="photosynthesis")
    result = ListeningVerbatimAnswerRule().evaluate(make_item_context(item))
    assert result.passed


def test_r_list_002_passes_for_spoken_dialogue() -> None:
    script = make_script(
        turns=[
            ("S1", "Good morning. How can I help you today?"),
            ("S2", "Hi, I'm interested — what's the monthly fee?"),
        ]
    )
    result = ListeningSpokenRegisterRule().evaluate(make_script_context(script))
    assert result.passed


def test_r_list_004_fails_for_unknown_speaker() -> None:
    script = make_script(turns=[("S9", "Hello there.")])
    result = ListeningSpeakerLabelRule().evaluate(make_script_context(script))
    assert not result.passed


def test_r_list_008_fails_for_raw_digit_sequence() -> None:
    script = make_script(turns=[("S1", "Call us on 07941234567 please.")])
    result = ListeningSpokenNumbersRule().evaluate(make_script_context(script))
    assert not result.passed
