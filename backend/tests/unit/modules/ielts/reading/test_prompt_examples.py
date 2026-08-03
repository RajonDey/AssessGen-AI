"""Prompt JSON example helpers."""

import json

from app.domain.enums import ItemType
from app.modules.ielts.reading.prompt_examples import (
    answer_batch_json_example,
    passage_json_example,
    question_batch_json_example,
    reviser_output_json_example,
)
from tests.unit.modules.ielts.reading.conftest import make_completion_item, make_passage


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


def test_passage_json_example_lists_multiple_paragraphs() -> None:
    payload = passage_json_example(paragraph_count=4)
    assert payload.count('"label"') == 4


def test_reviser_output_example_matches_schema_shape() -> None:
    passage = make_passage(title="Urban farming")
    item = make_completion_item(passage=passage)
    payload = json.loads(
        reviser_output_json_example(passage=passage, items=(item,)),
    )
    assert payload["passage"]["title"] == "Urban farming"
    assert payload["passage"]["paragraphs"][0]["label"] == "A"
    assert "text" in payload["passage"]["paragraphs"][0]
    assert len(payload["items"]) == 1
