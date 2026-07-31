"""Reading passage adaptor agent (Mode B — licensed source text)."""

from __future__ import annotations

from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.types import LLMRole
from app.modules.ielts.reading.agent_schemas import PassageAdaptorInput
from app.modules.ielts.reading.agents._helpers import build_user_message, prompt_hash_for
from app.modules.ielts.reading.bands import fk_grade_range
from app.modules.ielts.reading.prompts import passage_adaptor_prompt
from app.modules.ielts.reading.schemas import ReadingPassage


class ReadingPassageAdaptorAgent:
    async def run(self, gateway: LLMGateway, input: PassageAdaptorInput) -> ReadingPassage:
        plan = input.plan
        fk_min, fk_max = fk_grade_range(plan.target_band)
        template = passage_adaptor_prompt()
        values = {
            "license_label": input.license_label,
            "adaptation_level": input.adaptation_level,
            "source_text": input.source_text,
            "topic_angle": plan.topic_angle,
            "target_band": plan.target_band,
            "genre": plan.genre,
            "word_count_target": plan.word_count_target,
            "fk_grade_min": fk_min,
            "fk_grade_max": fk_max,
        }
        messages = (build_user_message(template, **values),)
        return await gateway.complete(
            role=LLMRole.GENERATOR,
            agent="reading_passage_adaptor",
            run_id=input.run_id,
            messages=messages,
            schema=ReadingPassage,
            prompt_hash=prompt_hash_for(template, **values),
        )
