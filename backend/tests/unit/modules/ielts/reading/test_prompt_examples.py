"""Prompt JSON example helpers."""

from app.domain.enums import ItemType
from app.modules.ielts.reading.prompt_examples import (
    answer_batch_json_example,
    question_batch_json_example,
)


def test_question_batch_example_is_valid_json() -> None:
    payload = question_batch_json_example(
        item_type=ItemType.SENTENCE_COMPLETION,
        count=2,
        instructions="NO MORE THAN TWO WORDS AND/OR A NUMBER",
    )
    assert '"items"' in payload
    assert payload.count("sentence_completion") == 2


def test_answer_batch_example_is_valid_json() -> None:
    payload = answer_batch_json_example(
        item_type=ItemType.SENTENCE_COMPLETION,
        count=1,
        instructions="NO MORE THAN TWO WORDS AND/OR A NUMBER",
    )
    assert '"answer_key"' in payload
    assert '"evidence"' in payload
