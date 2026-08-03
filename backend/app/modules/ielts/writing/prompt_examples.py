"""JSON examples for Writing agent prompts."""

from __future__ import annotations

import json

from app.modules.ielts.writing.schemas import WritingTask2Prompt


def task2_json_example(*, question_type: str = "opinion") -> str:
    samples: dict[str, WritingTask2Prompt] = {
        "opinion": WritingTask2Prompt(
            question_type="opinion",
            topic="Urban green spaces",
            prompt=(
                "Many cities are investing in parks and urban green spaces to improve "
                "residents' quality of life.\n\n"
                "To what extent do you agree or disagree that public funding for urban "
                "green spaces should be a priority for city governments?\n\n"
                "Give reasons for your answer and include any relevant examples from "
                "your own knowledge or experience.\n\n"
                "Write at least 250 words."
            ),
        ),
        "discussion": WritingTask2Prompt(
            question_type="discussion",
            topic="Remote work",
            prompt=(
                "Some people believe employees are more productive when working from home, "
                "while others argue that office-based work leads to better collaboration.\n\n"
                "Discuss both these views and give your own opinion.\n\n"
                "Give reasons for your answer and include any relevant examples.\n\n"
                "Write at least 250 words."
            ),
        ),
        "problem_solution": WritingTask2Prompt(
            question_type="problem_solution",
            topic="Plastic waste",
            prompt=(
                "Plastic waste in oceans and landfills is a growing environmental problem "
                "in many countries.\n\n"
                "What are the causes of this problem, and what solutions can be suggested "
                "to reduce plastic waste?\n\n"
                "Give reasons for your answer and include any relevant examples.\n\n"
                "Write at least 250 words."
            ),
        ),
        "advantages_disadvantages": WritingTask2Prompt(
            question_type="advantages_disadvantages",
            topic="International tourism",
            prompt=(
                "International tourism brings economic benefits to many destinations, "
                "but it can also create social and environmental pressures.\n\n"
                "Do the advantages of international tourism outweigh the disadvantages?\n\n"
                "Give reasons for your answer and include any relevant examples.\n\n"
                "Write at least 250 words."
            ),
        ),
        "two_part": WritingTask2Prompt(
            question_type="two_part",
            topic="Early education",
            prompt=(
                "In many countries, children begin formal schooling at the age of five or six.\n\n"
                "Why is early education considered important? "
                "What can parents and schools do to support children's learning in early years?\n\n"
                "Give reasons for your answer and include any relevant examples.\n\n"
                "Write at least 250 words."
            ),
        ),
    }
    sample = samples.get(question_type, samples["opinion"])
    return json.dumps(sample.model_dump(mode="json"), indent=2)
