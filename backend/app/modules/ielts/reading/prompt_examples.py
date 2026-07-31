"""JSON shape examples for small-model structured output."""

from __future__ import annotations

import json

from app.domain.enums import ItemType


def question_batch_json_example(
    *,
    item_type: ItemType,
    count: int,
    instructions: str,
) -> str:
    type_value = item_type.value
    if item_type == ItemType.HEADING_MATCH:
        sample = {
            "item_type": type_value,
            "stem": "Choose the correct heading for each paragraph.",
            "instructions": None,
            "options": [],
        }
    else:
        sample = {
            "item_type": type_value,
            "stem": "Engineers monitor _____ levels during each growing cycle.",
            "instructions": instructions,
        }
    payload = {"items": [sample for _ in range(max(1, count))]}
    return json.dumps(payload, indent=2)


def answer_batch_json_example(
    *,
    item_type: ItemType,
    count: int,
    instructions: str,
) -> str:
    type_value = item_type.value
    if item_type == ItemType.HEADING_MATCH:
        sample = {
            "item_type": type_value,
            "stem": "Choose the correct heading for each paragraph.",
            "instructions": None,
            "options": ["Heading 1", "Heading 2", "Heading 3", "Heading 4"],
            "answer_key": {"type": "mapping", "values": {"A": "1", "B": "2", "C": "3"}},
            "evidence": None,
            "explanation": "Each paragraph maps to one heading.",
        }
    else:
        sample = {
            "item_type": type_value,
            "stem": "Engineers monitor _____ levels during each growing cycle.",
            "instructions": instructions,
            "answer_key": {
                "type": "exact",
                "values": ["humidity"],
                "accept": [],
                "case_sensitive": False,
            },
            "evidence": {
                "paragraph": "A",
                "start": 42,
                "end": 50,
                "quote": "humidity",
            },
            "explanation": "Paragraph A names humidity explicitly.",
        }
    payload = {"items": [sample for _ in range(max(1, count))]}
    return json.dumps(payload, indent=2)
