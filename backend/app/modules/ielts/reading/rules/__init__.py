"""Register Academic Reading quality rules for Phase 1B."""

from __future__ import annotations

from app.domain.quality.protocol import Rule
from app.domain.quality.registry import RuleRegistry
from app.modules.ielts.reading.rules.r_comp_001 import CompletionVerbatimAnswerRule
from app.modules.ielts.reading.rules.r_comp_002 import CompletionWordLimitRule
from app.modules.ielts.reading.rules.r_comp_003 import CompletionLegalPhrasingRule
from app.modules.ielts.reading.rules.r_comp_004 import CompletionAlternateAnswersRule
from app.modules.ielts.reading.rules.r_comp_005 import CompletionGapGrammarRule
from app.modules.ielts.reading.rules.r_comp_006 import CompletionNotFunctionWordRule
from app.modules.ielts.reading.rules.r_head_001 import HeadingDistractorCountRule
from app.modules.ielts.reading.rules.r_head_002 import HeadingBijectionRule
from app.modules.ielts.reading.rules.r_head_003 import HeadingParagraphExistsRule
from app.modules.ielts.reading.rules.r_head_004 import HeadingNounPhraseRule
from app.modules.ielts.reading.rules.r_head_005 import HeadingNoOpeningCopyRule
from app.modules.ielts.reading.rules.r_item_001 import ItemStemLengthRule
from app.modules.ielts.reading.rules.r_item_002 import ItemNoAnswerLeakageRule
from app.modules.ielts.reading.rules.r_item_003 import ItemAnswerKeyWellFormedRule
from app.modules.ielts.reading.rules.r_item_004 import ItemEvidenceBoundsRule
from app.modules.ielts.reading.rules.r_item_005 import ItemEvidenceQuoteMatchRule
from app.modules.ielts.reading.rules.r_item_006 import ItemNoDuplicateStemRule
from app.modules.ielts.reading.rules.r_item_007 import ItemEstimatedTimeRule
from app.modules.ielts.reading.rules.r_item_008 import ItemInstructionsMatchTypeRule
from app.modules.ielts.reading.rules.r_pass_001 import PassageWordCountRule
from app.modules.ielts.reading.rules.r_pass_002 import PassageParagraphLabelsRule
from app.modules.ielts.reading.rules.r_pass_003 import PassageNoMetaTextRule
from app.modules.ielts.reading.rules.r_pass_004 import PassageReadabilityRule
from app.modules.ielts.reading.rules.r_pass_005 import PassageVocabularyProfileRule
from app.modules.ielts.reading.rules.r_pass_006 import PassageSentenceVarianceRule
from app.modules.ielts.reading.rules.r_pass_007 import PassageNoSecondPersonRule
from app.modules.ielts.reading.rules.r_pass_008 import PassageParagraphCountRule
from app.modules.ielts.reading.rules.r_pass_009 import PassageNoContradictionRule
from app.modules.ielts.reading.rules.r_set_001 import SetItemCountRule
from app.modules.ielts.reading.rules.r_set_002 import SetTypeMixRule
from app.modules.ielts.reading.rules.r_set_003 import SetPassageOrderRule
from app.modules.ielts.reading.rules.r_set_004 import SetDifficultyProgressionRule
from app.modules.ielts.reading.rules.r_set_005 import SetAnswerSpreadRule
from app.modules.ielts.reading.rules.r_set_006 import SetNoDuplicateFactRule

PASSAGE_RULES = (
    PassageWordCountRule(),
    PassageParagraphLabelsRule(),
    PassageNoMetaTextRule(),
    PassageReadabilityRule(),
    PassageVocabularyProfileRule(),
    PassageSentenceVarianceRule(),
    PassageNoSecondPersonRule(),
    PassageParagraphCountRule(),
    PassageNoContradictionRule(),
)

ITEM_RULES = (
    ItemStemLengthRule(),
    ItemNoAnswerLeakageRule(),
    ItemAnswerKeyWellFormedRule(),
    ItemEvidenceBoundsRule(),
    ItemEvidenceQuoteMatchRule(),
    ItemNoDuplicateStemRule(),
    ItemEstimatedTimeRule(),
    ItemInstructionsMatchTypeRule(),
    CompletionVerbatimAnswerRule(),
    CompletionWordLimitRule(),
    CompletionLegalPhrasingRule(),
    CompletionAlternateAnswersRule(),
    CompletionGapGrammarRule(),
    CompletionNotFunctionWordRule(),
    HeadingDistractorCountRule(),
    HeadingBijectionRule(),
    HeadingParagraphExistsRule(),
    HeadingNounPhraseRule(),
    HeadingNoOpeningCopyRule(),
)

SET_RULES = (
    SetItemCountRule(),
    SetTypeMixRule(),
    SetPassageOrderRule(),
    SetDifficultyProgressionRule(),
    SetAnswerSpreadRule(),
    SetNoDuplicateFactRule(),
)


def _register(registry: RuleRegistry, rules: tuple[Rule, ...]) -> RuleRegistry:
    for rule in rules:
        registry.register(rule)
    return registry


def build_passage_rule_registry() -> RuleRegistry:
    return _register(RuleRegistry(), PASSAGE_RULES)


def build_item_rule_registry() -> RuleRegistry:
    return _register(RuleRegistry(), ITEM_RULES)


def build_set_rule_registry() -> RuleRegistry:
    return _register(RuleRegistry(), SET_RULES)


def build_reading_rule_registry() -> RuleRegistry:
    registry = RuleRegistry()
    for rule in (*PASSAGE_RULES, *ITEM_RULES, *SET_RULES):
        registry.register(rule)
    return registry
