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
