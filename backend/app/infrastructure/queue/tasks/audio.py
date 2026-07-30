"""Audio/TTS tasks — wired for Phase 3, idle in 1A."""

from app.infrastructure.queue.base import AssessGenTask
from app.infrastructure.queue.celery_app import celery_app


@celery_app.task(
    name="app.infrastructure.queue.tasks.ping_audio",
    base=AssessGenTask,
    bind=True,
)
def ping_audio(self: AssessGenTask, payload: str = "ping") -> dict[str, str]:
    """Queue wiring probe for q.audio."""
    return {
        "status": "ok",
        "payload": payload,
        "queue": "q.audio",
        "task_id": self.request.id or "",
    }
