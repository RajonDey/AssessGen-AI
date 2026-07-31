"""Reading answer generator agent — keys, evidence, and explanations."""

from __future__ import annotations

from app.domain.enums import ItemType
from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.types import LLMRole
from app.modules.ielts.reading.agent_schemas import AnswerBatchOutput, AnswerGeneratorInput
from app.modules.ielts.reading.agents._helpers import (
    build_user_message,
    drafts_to_json,
    prompt_hash_for,
)
from app.modules.ielts.reading.prompt_examples import answer_batch_json_example
from app.modules.ielts.reading.prompts import answer_prompt


class ReadingAnswerGeneratorAgent:
    async def run(self, gateway: LLMGateway, input: AnswerGeneratorInput) -> AnswerBatchOutput:
        if not input.drafts:
            msg = "At least one question draft is required"
            raise ValueError(msg)

        item_type = input.drafts[0].item_type
        if any(draft.item_type != item_type for draft in input.drafts):
            msg = "Answer generator expects a homogeneous batch of one item type"
            raise ValueError(msg)

        template = answer_prompt(item_type=item_type.value)
        instructions = input.drafts[0].instructions or "NO MORE THAN TWO WORDS AND/OR A NUMBER"
        values = {
            "passage_title": input.passage.title,
            "passage_body": input.passage.body,
            "items_json": drafts_to_json(input.drafts),
            "paragraph_count": len(input.passage.paragraphs),
            "json_example": answer_batch_json_example(
                item_type=item_type,
                count=len(input.drafts),
                instructions=instructions,
            ),
        }
        messages = (build_user_message(template, **values),)
        result = await gateway.complete(
            role=LLMRole.GENERATOR,
            agent="reading_answer_generator",
            run_id=input.run_id,
            messages=messages,
            schema=AnswerBatchOutput,
            prompt_hash=prompt_hash_for(template, **values),
        )
        if len(result.items) != len(input.drafts):
            msg = f"Expected {len(input.drafts)} answered items, got {len(result.items)}"
            raise ValueError(msg)

        if item_type == ItemType.HEADING_MATCH:
            for answered in result.items:
                if answered.evidence is not None:
                    msg = "Heading match items must not include evidence spans"
                    raise ValueError(msg)
        else:
            for answered in result.items:
                if answered.evidence is None:
                    msg = "Completion items require evidence spans"
                    raise ValueError(msg)

        return result
