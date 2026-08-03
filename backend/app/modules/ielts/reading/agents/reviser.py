"""Reading reviser agent — targeted repairs from rule or critic findings."""

from __future__ import annotations

import json

from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.types import LLMRole
from app.modules.ielts.reading.agent_schemas import ReviserInput, ReviserOutput
from app.modules.ielts.reading.agents._helpers import (
    build_user_message,
    models_to_json,
    prompt_hash_for,
)
from app.modules.ielts.reading.helpers import normalize_item_evidence
from app.modules.ielts.reading.prompt_examples import reviser_output_json_example
from app.modules.ielts.reading.prompts import reviser_prompt
from app.modules.ielts.reading.spec import AcademicReadingSpec


class ReadingReviserAgent:
    async def run(self, gateway: LLMGateway, input: ReviserInput) -> ReviserOutput:
        template = reviser_prompt()
        findings_json = json.dumps(
            [finding.model_dump(mode="json") for finding in input.findings],
            indent=2,
        )
        values = {
            "findings_json": findings_json,
            "passage_title": input.passage.title,
            "passage_body": input.passage.body,
            "items_json": models_to_json(input.items),
            "word_count_min": AcademicReadingSpec().passage_word_count_min,
            "json_example": reviser_output_json_example(
                passage=input.passage,
                items=input.items,
            ),
        }
        messages = (build_user_message(template, **values),)
        result = await gateway.complete(
            role=LLMRole.GENERATOR,
            agent="reading_reviser",
            run_id=input.run_id,
            messages=messages,
            schema=ReviserOutput,
            prompt_hash=prompt_hash_for(template, **values),
        )
        if len(result.items) != len(input.items):
            msg = f"Reviser must return {len(input.items)} items, got {len(result.items)}"
            raise ValueError(msg)
        normalized_items = [
            normalize_item_evidence(result.passage, item) for item in result.items
        ]
        return ReviserOutput(passage=result.passage, items=normalized_items)
