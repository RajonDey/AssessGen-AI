"""Celery task error taxonomy — content failures must not retry."""


class ContentTaskError(Exception):
    """Business/content failure inside a task — fail the job, do not retry."""


class InfrastructureTaskError(Exception):
    """Transient infrastructure failure — Celery may retry with backoff."""
