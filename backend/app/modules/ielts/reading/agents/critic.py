"""Reading critic agent — structured findings only."""

from __future__ import annotations

from app.domain.quality.critic import CriticOutput
from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.types import LLMRole
from app.modules.ielts.reading.agent_schemas import CriticInput
from app.modules.ielts.reading.agents._helpers import (
    build_user_message,
    models_to_json,
    prompt_hash_for,
)
from app.modules.ielts.reading.prompts import critic_prompt


class ReadingCriticAgent:
    async def run(self, gateway: LLMGateway, input: CriticInput) -> CriticOutput:
        template = critic_prompt()
        values = {
            "passage_title": input.passage.title,
            "passage_body": input.passage.body,
            "item_count": len(input.items),
            "items_json": models_to_json(input.items),
        }
        messages = (build_user_message(template, **values),)
        return await gateway.complete(
            role=LLMRole.CRITIC,
            agent="reading_critic",
            run_id=input.run_id,
            messages=messages,
            schema=CriticOutput,
            prompt_hash=prompt_hash_for(template, **values),
        )
