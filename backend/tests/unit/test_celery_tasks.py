"""Celery task behaviour tests."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from app.infrastructure.queue.base import AssessGenTask
from app.infrastructure.queue.celery_app import celery_app
from app.infrastructure.queue.errors import ContentTaskError, InfrastructureTaskError
from app.infrastructure.queue.tasks.io import ping_io
from celery import Task


@pytest.fixture
def celery_eager() -> Generator[None, None, None]:
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = False
    celery_app.conf.task_eager_propagates = False


def test_assessgen_task_retry_policy() -> None:
    assert InfrastructureTaskError in AssessGenTask.autoretry_for
    assert ContentTaskError in AssessGenTask.dont_autoretry_for
    assert AssessGenTask.max_retries == 3


def test_ping_io_completes_in_eager_mode(celery_eager: None) -> None:
    result = ping_io.apply(args=["hello"]).get()
    assert result["status"] == "ok"
    assert result["payload"] == "hello"
    assert result["queue"] == "q.io"


@celery_app.task(bind=True, base=AssessGenTask, name="tests.celery.content_fail_probe")  # type: ignore[untyped-decorator]
def _content_fail_probe(_self: Task) -> None:
    raise ContentTaskError("content rejected")


@celery_app.task(bind=True, base=AssessGenTask, name="tests.celery.infra_fail_probe")  # type: ignore[untyped-decorator]
def _infra_fail_probe(self: Task) -> str:
    if self.request.retries < 2:
        raise InfrastructureTaskError("provider down")
    return "recovered"


def test_content_failure_is_not_retried(celery_eager: None) -> None:
    with pytest.raises(ContentTaskError):
        _content_fail_probe.apply().get()
    assert _content_fail_probe.request.retries == 0


def test_infrastructure_failure_triggers_celery_retry(celery_eager: None) -> None:
    from celery.exceptions import Retry

    with pytest.raises(Retry):
        _infra_fail_probe.apply().get()
