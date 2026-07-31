"""Domain enums shared across all exam modules."""

from enum import StrEnum


class Module(StrEnum):
    READING = "reading"
    LISTENING = "listening"
    WRITING = "writing"
    SPEAKING = "speaking"


class ItemStatus(StrEnum):
    DRAFT = "draft"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class Severity(StrEnum):
    MUST = "must"
    SHOULD = "should"
    INFO = "info"


class UserRole(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class ItemType(StrEnum):
    """Reading item types — Phase 1B target set (types 1–5)."""

    SENTENCE_COMPLETION = "sentence_completion"
    SUMMARY_COMPLETION = "summary_completion"
    SHORT_ANSWER = "short_answer"
    NOTE_COMPLETION = "note_completion"
    HEADING_MATCH = "heading_match"


class PassageSourceMode(StrEnum):
    """How passage body text is obtained before question generation."""

    GENERATED = "generated"
    INGESTED = "ingested"
    ADAPTED = "adapted"


class FindingCategory(StrEnum):
    """LLM critic finding categories — structured review signals only."""

    AMBIGUITY = "ambiguity"
    WEAK_DISTRACTOR = "weak_distractor"
    MULTIPLE_DEFENSIBLE_ANSWERS = "multiple_defensible_answers"
    REGISTER_MISMATCH = "register_mismatch"
    FACTUAL_DOUBT = "factual_doubt"
    CULTURAL_BIAS = "cultural_bias"
    AWKWARD_PHRASING = "awkward_phrasing"
    ANSWER_NOT_SUPPORTED = "answer_not_supported"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    FAILED = "failed"
