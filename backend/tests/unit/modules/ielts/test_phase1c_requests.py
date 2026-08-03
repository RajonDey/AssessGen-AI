"""Unit tests for Phase 1C module request parsers."""

import pytest

from app.modules.ielts.listening.request import parse_listening_spec
from app.modules.ielts.speaking.request import parse_speaking_spec
from app.modules.ielts.writing.request import parse_writing_spec


def test_parse_listening_spec_defaults() -> None:
    spec = parse_listening_spec({"module": "listening"})
    assert spec.section == 1
    assert spec.question_count == 10


def test_parse_listening_spec_rejects_section_3_in_1c() -> None:
    with pytest.raises(ValueError, match="Invalid listening"):
        parse_listening_spec({"spec": {"section": 3, "topic": "Test"}})


def test_parse_writing_spec_question_type() -> None:
    spec = parse_writing_spec({"spec": {"topic": "Climate", "question_type": "discussion"}})
    assert spec.question_type == "discussion"


def test_parse_speaking_spec_defaults() -> None:
    spec = parse_speaking_spec({"module": "speaking"})
    assert spec.topic_domain == "Learning and skills"
