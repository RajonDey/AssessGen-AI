"""R-PASS-006 tests."""

from app.modules.ielts.reading.rules.r_pass_006 import PassageSentenceVarianceRule
from tests.unit.modules.ielts.reading.conftest import make_context


def test_varied_sentences_pass() -> None:
    text = (
        "Short line. "
        "This sentence is moderately longer than the first one. "
        "And this final sentence adds even more length and detail to the paragraph."
    )
    context = make_context(paragraphs=[("A", text)])
    assert PassageSentenceVarianceRule().evaluate(context).passed


def test_flat_rhythm_fails() -> None:
    text = "Words repeat. Words repeat. Words repeat. Words repeat."
    context = make_context(paragraphs=[("A", text)])
    assert not PassageSentenceVarianceRule().evaluate(context).passed
