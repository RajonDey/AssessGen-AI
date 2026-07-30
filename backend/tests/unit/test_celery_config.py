"""Celery configuration tests."""

from app.infrastructure.queue.celery_app import celery_app
from app.infrastructure.queue.constants import ALL_QUEUES, AUDIO_QUEUE, GENERATE_QUEUE, IO_QUEUE


def test_three_queues_are_configured() -> None:
    queue_names = {queue.name for queue in celery_app.conf.task_queues}
    assert queue_names == set(ALL_QUEUES)


def test_generation_task_routes_to_generate_queue() -> None:
    routes = celery_app.conf.task_routes
    assert routes["app.workflows.generation_tasks.run_generation"]["queue"] == GENERATE_QUEUE


def test_io_and_audio_tasks_route_to_expected_queues() -> None:
    routes = celery_app.conf.task_routes
    assert routes["app.infrastructure.queue.tasks.ping_io"]["queue"] == IO_QUEUE
    assert routes["app.infrastructure.queue.tasks.ping_audio"]["queue"] == AUDIO_QUEUE


def test_late_ack_and_worker_loss_rejection_enabled() -> None:
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
