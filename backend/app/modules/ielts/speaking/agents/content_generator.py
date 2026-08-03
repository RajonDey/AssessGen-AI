"""IELTS Speaking Part 1 + Part 2 generator agent."""

from __future__ import annotations

from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.types import LLMRole
from app.modules.ielts.speaking.agent_schemas import ContentGeneratorInput
from app.modules.ielts.speaking.agents._helpers import build_user_message, prompt_hash_for
from app.modules.ielts.speaking.prompt_examples import speaking_content_json_example
from app.modules.ielts.speaking.prompts import part1_part2_prompt
from app.modules.ielts.speaking.schemas import SpeakingPart1And2


class SpeakingContentGeneratorAgent:
    async def run(
        self,
        gateway: LLMGateway,
        input: ContentGeneratorInput,
    ) -> SpeakingPart1And2:
        template = part1_part2_prompt()
        values = {
            "topic_domain": input.topic_domain,
            "target_band": input.target_band,
            "json_example": speaking_content_json_example(),
        }
        messages = (build_user_message(template, **values),)
        return await gateway.complete(
            role=LLMRole.GENERATOR,
            agent="speaking_content_generator",
            run_id=input.run_id,
            messages=messages,
            schema=SpeakingPart1And2,
            prompt_hash=prompt_hash_for(template, **values),
        )
