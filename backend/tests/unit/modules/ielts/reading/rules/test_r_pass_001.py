"""R-PASS-001 tests."""

from app.modules.ielts.reading.rules.r_pass_001 import PassageWordCountRule
from tests.unit.modules.ielts.reading.conftest import make_context


def test_word_count_within_bounds_passes() -> None:
    body = " ".join(["word"] * 800)
    context = make_context(
        paragraphs=[("A", body)],
        word_count_min=700,
        word_count_max=1000,
    )
    assert PassageWordCountRule().evaluate(context).passed


def test_word_count_below_min_fails() -> None:
    context = make_context(
        paragraphs=[("A", "too short")],
        word_count_min=700,
        word_count_max=1000,
    )
    assert not PassageWordCountRule().evaluate(context).passed
