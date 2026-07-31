"""R-PASS-007 tests."""

from app.modules.ielts.reading.rules.r_pass_007 import PassageNoSecondPersonRule
from tests.unit.modules.ielts.reading.conftest import make_context


def test_third_person_passes() -> None:
    context = make_context(paragraphs=[("A", "The researchers published their findings.")])
    assert PassageNoSecondPersonRule().evaluate(context).passed


def test_second_person_fails() -> None:
    context = make_context(paragraphs=[("A", "You will learn how cities adapt.")])
    result = PassageNoSecondPersonRule().evaluate(context)
    assert not result.passed
    assert result.detail["patterns_matched"]
