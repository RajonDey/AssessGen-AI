"""Celery application — Redis broker and queue routing."""

from celery import Celery
from celery.signals import worker_process_init
from kombu import Queue

from app.config import get_settings
from app.infrastructure.observability.logging import configure_logging
from app.infrastructure.queue.constants import ALL_QUEUES, AUDIO_QUEUE, GENERATE_QUEUE, IO_QUEUE

settings = get_settings()

celery_app = Celery(
    "assessgen",
    broker=str(settings.redis_url),
    backend=str(settings.redis_url),
    include=[
        "app.infrastructure.queue.tasks.io",
        "app.infrastructure.queue.tasks.audio",
        "app.workflows.generation_tasks",
    ],
)

celery_app.conf.update(
    task_default_queue=IO_QUEUE,
    task_queues=tuple(Queue(name) for name in ALL_QUEUES),
    task_routes={
        "app.workflows.generation_tasks.run_generation": {"queue": GENERATE_QUEUE},
        "app.infrastructure.queue.tasks.ping_io": {"queue": IO_QUEUE},
        "app.infrastructure.queue.tasks.ping_audio": {"queue": AUDIO_QUEUE},
    },
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    result_expires=3600,
    task_default_retry_delay=30,
)

import app.infrastructure.queue.tasks  # noqa: E402, F401


@worker_process_init.connect
def _configure_worker_logging(**_kwargs: object) -> None:
    configure_logging(get_settings())
