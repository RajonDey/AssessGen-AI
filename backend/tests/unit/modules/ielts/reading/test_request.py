"""Unit tests for reading request parsing."""

import pytest

from app.domain.enums import PassageSourceMode
from app.modules.ielts.reading.request import parse_reading_spec, validate_plan_counts


def _long_source_text(word_count: int = 750) -> str:
    sentence = (
        "Urban vertical farms convert sunlight through photosynthesis into stored energy "
        "while engineers monitor humidity levels across each growing cycle."
    )
    words: list[str] = []
    while len(words) < word_count:
        words.extend(sentence.split())
    return " ".join(words[:word_count])


def test_parse_reading_spec_defaults() -> None:
    spec = parse_reading_spec({"module": "reading"})
    assert spec.topic == "General science"
    assert spec.question_count == 13
    assert spec.source_mode == PassageSourceMode.GENERATED


def test_parse_reading_spec_from_nested_spec() -> None:
    spec = parse_reading_spec(
        {
            "spec": {
                "topic": "Climate policy",
                "question_count": 2,
                "source_mode": "adapted",
                "source_text": _long_source_text(),
                "license_label": "CC-BY-4.0",
            }
        }
    )
    assert spec.topic == "Climate policy"
    assert spec.question_count == 2
    assert spec.source_mode == PassageSourceMode.ADAPTED


def test_validate_plan_counts() -> None:
    ok, _ = validate_plan_counts(block_total=13, question_count=13)
    assert ok
    bad, reason = validate_plan_counts(block_total=10, question_count=13)
    assert not bad
    assert "10" in reason


def test_parse_reading_spec_requires_source_text_for_ingested() -> None:
    with pytest.raises(ValueError, match="source_text"):
        parse_reading_spec({"spec": {"source_mode": "ingested", "topic": "Test"}})


def test_parse_reading_spec_rejects_short_ingested_text() -> None:
    short_text = " ".join(["word"] * 120)
    with pytest.raises(ValueError, match="700"):
        parse_reading_spec(
            {
                "spec": {
                    "source_mode": "ingested",
                    "topic": "Test",
                    "source_text": short_text,
                }
            }
        )
