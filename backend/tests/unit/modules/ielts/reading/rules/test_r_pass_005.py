"""R-PASS-005 tests."""

from app.modules.ielts.reading.rules.r_pass_005 import PassageVocabularyProfileRule
from tests.unit.modules.ielts.reading.conftest import make_context


def test_vocabulary_rule_returns_ratio_detail() -> None:
    text = "The city built new parks and schools for local communities."
    context = make_context(paragraphs=[("A", text)])
    result = PassageVocabularyProfileRule().evaluate(context)
    assert "rare_word_ratio" in result.detail
    assert 0.0 <= result.detail["rare_word_ratio"] <= 1.0


def test_unicode_input_does_not_raise() -> None:
    context = make_context(paragraphs=[("A", "Café résumé naïve — urbanité.")])
    PassageVocabularyProfileRule().evaluate(context)
