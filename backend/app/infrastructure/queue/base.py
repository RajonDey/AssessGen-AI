"""Shared Celery task base with retry policy."""

from celery import Task

from app.infrastructure.queue.errors import ContentTaskError, InfrastructureTaskError


class AssessGenTask(Task):
    """Retry only infrastructure failures — never content failures."""

    autoretry_for = (InfrastructureTaskError,)
    dont_autoretry_for = (ContentTaskError,)
    max_retries = 3
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True

    # Content failures should not hold the message for redelivery.
    acks_late = True
    reject_on_worker_lost = True
