"""Reading passage generator agent (Mode A — AI-written)."""

from __future__ import annotations

from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.types import LLMRole
from app.modules.ielts.reading.agent_schemas import PassageGeneratorInput
from app.modules.ielts.reading.agents._helpers import build_user_message, prompt_hash_for
from app.modules.ielts.reading.bands import fk_grade_range
from app.modules.ielts.reading.prompt_examples import passage_json_example
from app.modules.ielts.reading.prompts import passage_prompt
from app.modules.ielts.reading.schemas import ReadingPassage
from app.modules.ielts.reading.spec import AcademicReadingSpec


class ReadingPassageGeneratorAgent:
    async def run(self, gateway: LLMGateway, input: PassageGeneratorInput) -> ReadingPassage:
        plan = input.plan
        fk_min, fk_max = fk_grade_range(plan.target_band)
        question_count = sum(block.count for block in plan.question_blocks)
        bounds = AcademicReadingSpec()
        paragraph_count = max(4, len(plan.question_blocks) + 2)
        template = passage_prompt(variant="academic")
        values = {
            "topic_angle": plan.topic_angle,
            "target_band": plan.target_band,
            "genre": plan.genre,
            "word_count_target": plan.word_count_target,
            "word_count_min": bounds.passage_word_count_min,
            "word_count_max": bounds.passage_word_count_max,
            "fk_grade_min": fk_min,
            "fk_grade_max": fk_max,
            "passage_index": plan.passage_index + 1,
            "question_count": question_count,
            "json_example": passage_json_example(paragraph_count=paragraph_count),
        }
        messages = (build_user_message(template, **values),)
        return await gateway.complete(
            role=LLMRole.GENERATOR,
            agent="reading_passage_generator",
            run_id=input.run_id,
            messages=messages,
            schema=ReadingPassage,
            prompt_hash=prompt_hash_for(template, **values),
        )
