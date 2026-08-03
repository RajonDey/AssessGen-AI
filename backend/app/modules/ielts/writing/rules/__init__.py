"""Register IELTS Writing quality rules for Phase 1C."""

from __future__ import annotations

from app.domain.quality.protocol import Rule
from app.domain.quality.registry import RuleRegistry
from app.modules.ielts.writing.rules.r_writ_001 import WritingClearPropositionRule
from app.modules.ielts.writing.rules.r_writ_002 import WritingQuestionTypeRule
from app.modules.ielts.writing.rules.r_writ_003 import WritingWordCountInstructionRule
from app.modules.ielts.writing.rules.r_writ_004 import WritingCulturalNeutralityRule
from app.modules.ielts.writing.rules.r_writ_005 import WritingNoSpecialistKnowledgeRule
from app.modules.ielts.writing.rules.r_writ_006 import WritingGtTask1LetterRule

PROMPT_RULES: tuple[Rule, ...] = (
    WritingClearPropositionRule(),
    WritingQuestionTypeRule(),
    WritingWordCountInstructionRule(),
    WritingCulturalNeutralityRule(),
    WritingNoSpecialistKnowledgeRule(),
    WritingGtTask1LetterRule(),
)


def build_prompt_rule_registry() -> RuleRegistry:
    registry = RuleRegistry()
    for rule in PROMPT_RULES:
        registry.register(rule)
    return registry
