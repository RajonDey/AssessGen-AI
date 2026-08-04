"""Speaking rule tests."""

from app.modules.ielts.speaking.rules.r_spk_001 import SpeakingPart2BulletCountRule
from app.modules.ielts.speaking.rules.r_spk_002 import SpeakingPart2ExplainPromptRule
from app.modules.ielts.speaking.rules.r_spk_003 import SpeakingPart1StructureRule
from app.modules.ielts.speaking.rules.r_spk_004 import SpeakingPart3CountRule
from app.modules.ielts.speaking.rules.r_spk_005 import SpeakingPart2BulletIndependenceRule
from tests.unit.modules.ielts.speaking.conftest import make_speaking_content, make_speaking_context


def test_r_spk_001_passes_with_three_bullets() -> None:
    content = make_speaking_content()
    result = SpeakingPart2BulletCountRule().evaluate(make_speaking_context(content))
    assert result.passed


def test_r_spk_002_passes_with_explain_prompt() -> None:
    content = make_speaking_content()
    result = SpeakingPart2ExplainPromptRule().evaluate(make_speaking_context(content))
    assert result.passed


def test_r_spk_003_passes_for_valid_part1_structure() -> None:
    content = make_speaking_content()
    result = SpeakingPart1StructureRule().evaluate(make_speaking_context(content))
    assert result.passed


def test_r_spk_004_skips_without_part3() -> None:
    content = make_speaking_content()
    result = SpeakingPart3CountRule().evaluate(make_speaking_context(content))
    assert result.passed
    assert result.detail.get("skipped") is True


def test_r_spk_005_fails_for_redundant_bullets() -> None:
    content = make_speaking_content(
        bullets=[
            "what the skill was",
            "what the skill was",
            "how you learned it",
        ]
    )
    result = SpeakingPart2BulletIndependenceRule().evaluate(make_speaking_context(content))
    assert not result.passed
