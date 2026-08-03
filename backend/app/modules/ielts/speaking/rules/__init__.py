"""Register IELTS Speaking quality rules for Phase 1C."""

from __future__ import annotations

from app.domain.quality.protocol import Rule
from app.domain.quality.registry import RuleRegistry
from app.modules.ielts.speaking.rules.r_spk_001 import SpeakingPart2BulletCountRule
from app.modules.ielts.speaking.rules.r_spk_002 import SpeakingPart2ExplainPromptRule
from app.modules.ielts.speaking.rules.r_spk_003 import SpeakingPart1StructureRule
from app.modules.ielts.speaking.rules.r_spk_004 import SpeakingPart3CountRule
from app.modules.ielts.speaking.rules.r_spk_005 import SpeakingPart2BulletIndependenceRule

SPEAKING_RULES: tuple[Rule, ...] = (
    SpeakingPart2BulletCountRule(),
    SpeakingPart2ExplainPromptRule(),
    SpeakingPart1StructureRule(),
    SpeakingPart3CountRule(),
    SpeakingPart2BulletIndependenceRule(),
)


def build_speaking_rule_registry() -> RuleRegistry:
    registry = RuleRegistry()
    for rule in SPEAKING_RULES:
        registry.register(rule)
    return registry
