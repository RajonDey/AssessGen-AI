"""Writing rule tests."""

from app.modules.ielts.writing.rules.r_writ_001 import WritingClearPropositionRule
from app.modules.ielts.writing.rules.r_writ_002 import WritingQuestionTypeRule
from app.modules.ielts.writing.rules.r_writ_003 import WritingWordCountInstructionRule
from app.modules.ielts.writing.rules.r_writ_006 import WritingGtTask1LetterRule
from tests.unit.modules.ielts.writing.conftest import make_prompt_context, make_task2_prompt


def test_r_writ_001_passes_for_valid_opinion_prompt() -> None:
    prompt = make_task2_prompt()
    result = WritingClearPropositionRule().evaluate(make_prompt_context(prompt))
    assert result.passed


def test_r_writ_002_passes_for_discussion_prompt() -> None:
    prompt = make_task2_prompt(
        question_type="discussion",
        prompt=(
            "Some people believe remote work improves productivity, "
            "while others argue office collaboration is essential.\n\n"
            "Discuss both these views and give your own opinion.\n\n"
            "Write at least 250 words."
        ),
    )
    result = WritingQuestionTypeRule().evaluate(make_prompt_context(prompt))
    assert result.passed


def test_r_writ_003_requires_250_word_instruction() -> None:
    prompt = make_task2_prompt(word_count_instruction="Write at least 250 words.")
    result = WritingWordCountInstructionRule().evaluate(make_prompt_context(prompt))
    assert result.passed


def test_r_writ_006_skips_for_task_2() -> None:
    prompt = make_task2_prompt()
    result = WritingGtTask1LetterRule().evaluate(make_prompt_context(prompt))
    assert result.passed
    assert result.detail.get("skipped") is True
