"""I/O-bound Celery tasks."""

from app.infrastructure.queue.base import AssessGenTask
from app.infrastructure.queue.celery_app import celery_app


@celery_app.task(
    name="app.infrastructure.queue.tasks.ping_io",
    base=AssessGenTask,
    bind=True,
)
def ping_io(self: AssessGenTask, payload: str = "ping") -> dict[str, str]:
    """Health/dispatch probe for q.io — used in tests and ops checks."""
    return {
        "status": "ok",
        "payload": payload,
        "queue": "q.io",
        "task_id": self.request.id or "",
    }
