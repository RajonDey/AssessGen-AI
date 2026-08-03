"""R-SPK-003 — Part 1 has three topics with three to four questions each."""

from __future__ import annotations

from app.domain.enums import Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.speaking.context import SpeakingRuleContext
from app.modules.ielts.speaking.spec import SpeakingSpec


class SpeakingPart1StructureRule:
    code = "R-SPK-003"
    severity = Severity.MUST

    def evaluate(self, context: SpeakingRuleContext) -> RuleResult:
        bounds = SpeakingSpec()
        topic_count = len(context.part1_topics)
        question_counts = [len(topic.questions) for topic in context.part1_topics]
        topics_ok = topic_count == bounds.part1_topic_count
        questions_ok = all(
            bounds.part1_questions_min <= count <= bounds.part1_questions_max
            for count in question_counts
        )
        passed = topics_ok and questions_ok
        return RuleResult(
            rule_code=self.code,
            passed=passed,
            severity=self.severity,
            message="Part 1 has 3 topics with 3–4 questions each"
            if passed
            else "Part 1 topic/question structure invalid",
            detail={
                "topic_count": topic_count,
                "question_counts": question_counts,
                "expected_topics": bounds.part1_topic_count,
            },
        )
