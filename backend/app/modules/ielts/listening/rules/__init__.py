"""Register IELTS Listening quality rules for Phase 1C."""

from __future__ import annotations

from app.domain.quality.protocol import Rule
from app.domain.quality.registry import RuleRegistry
from app.modules.ielts.listening.rules.r_list_001 import ListeningVerbatimAnswerRule
from app.modules.ielts.listening.rules.r_list_002 import ListeningSpokenRegisterRule
from app.modules.ielts.listening.rules.r_list_003 import ListeningHesitationRule
from app.modules.ielts.listening.rules.r_list_004 import ListeningSpeakerLabelRule
from app.modules.ielts.listening.rules.r_list_005 import ListeningAnswerSpreadRule
from app.modules.ielts.listening.rules.r_list_006 import ListeningSelfCorrectionRule
from app.modules.ielts.listening.rules.r_list_007 import ListeningSpelledProperNounRule
from app.modules.ielts.listening.rules.r_list_008 import ListeningSpokenNumbersRule

LISTENING_ITEM_RULES: tuple[Rule, ...] = (ListeningVerbatimAnswerRule(),)

SCRIPT_RULES: tuple[Rule, ...] = (
    ListeningSpokenRegisterRule(),
    ListeningHesitationRule(),
    ListeningSpeakerLabelRule(),
    ListeningSelfCorrectionRule(),
    ListeningSpelledProperNounRule(),
    ListeningSpokenNumbersRule(),
)

ANSWER_SPREAD_RULE = ListeningAnswerSpreadRule()


def build_script_rule_registry() -> RuleRegistry:
    registry = RuleRegistry()
    for rule in SCRIPT_RULES:
        registry.register(rule)
    return registry
