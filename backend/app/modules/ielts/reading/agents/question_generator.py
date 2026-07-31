"""Reading question generator agent — batched by item type."""

from __future__ import annotations

from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.types import LLMRole
from app.modules.ielts.reading.agent_schemas import QuestionBatchOutput, QuestionGeneratorInput
from app.modules.ielts.reading.agents._helpers import build_user_message, prompt_hash_for
from app.modules.ielts.reading.prompt_examples import question_batch_json_example
from app.modules.ielts.reading.prompts import question_prompt


class ReadingQuestionGeneratorAgent:
    async def run(self, gateway: LLMGateway, input: QuestionGeneratorInput) -> QuestionBatchOutput:
        block = input.block
        passage = input.passage
        item_type = block.item_type.value
        template = question_prompt(item_type=item_type)
        values = {
            "passage_title": passage.title,
            "passage_body": passage.body,
            "item_count": block.count,
            "target_paragraphs": ", ".join(block.target_paragraphs) or "spread across passage",
            "instructions": block.instructions or "NO MORE THAN TWO WORDS AND/OR A NUMBER",
            "paragraph_count": len(passage.paragraphs),
            "json_example": question_batch_json_example(
                item_type=block.item_type,
                count=block.count,
                instructions=block.instructions or "NO MORE THAN TWO WORDS AND/OR A NUMBER",
            ),
        }
        messages = (build_user_message(template, **values),)
        result = await gateway.complete(
            role=LLMRole.GENERATOR,
            agent="reading_question_generator",
            run_id=input.run_id,
            messages=messages,
            schema=QuestionBatchOutput,
            prompt_hash=prompt_hash_for(template, **values),
        )
        if len(result.items) != block.count:
            msg = f"Expected {block.count} items, got {len(result.items)}"
            raise ValueError(msg)
        for item in result.items:
            if item.item_type != block.item_type:
                msg = f"Item type mismatch: expected {block.item_type}, got {item.item_type}"
                raise ValueError(msg)
        return result
