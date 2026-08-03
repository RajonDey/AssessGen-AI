"""JSON examples for Speaking agent prompts."""

from __future__ import annotations

import json

from app.modules.ielts.speaking.schemas import (
    SpeakingPart1And2,
    SpeakingPart1Topic,
    SpeakingPart2CueCard,
)


def speaking_content_json_example() -> str:
    sample = SpeakingPart1And2(
        part1_topics=[
            SpeakingPart1Topic(
                name="Learning",
                questions=[
                    "Do you enjoy learning new skills?",
                    "What did you study at school?",
                    "Do you prefer studying alone or with others?",
                    "What skill would you like to learn in the future?",
                ],
            ),
            SpeakingPart1Topic(
                name="Books and reading",
                questions=[
                    "Do you read books regularly?",
                    "What kind of books do you like?",
                    "Did you read much when you were a child?",
                ],
            ),
            SpeakingPart1Topic(
                name="Daily routine",
                questions=[
                    "What time do you usually wake up?",
                    "What is your favourite part of the day?",
                    "Has your routine changed recently?",
                    "Do you think routines are important?",
                ],
            ),
        ],
        part2=SpeakingPart2CueCard(
            topic="Describe a skill you learned that was difficult.",
            bullets=[
                "what the skill was",
                "when and why you learned it",
                "how you learned it",
            ],
            explain_prompt="and explain why you found it difficult.",
        ),
    )
    return json.dumps(sample.model_dump(mode="json"), indent=2)
