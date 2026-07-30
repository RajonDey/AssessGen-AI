"""Global model lease — one large model resident at a time."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis.asyncio import Redis


@dataclass(frozen=True, slots=True)
class LeaseToken:
    model: str
    memory_gb: float


class ModelLease(ABC):
    @asynccontextmanager
    async def hold(self, model: str, memory_gb: float) -> AsyncIterator[LeaseToken]:
        await self.acquire(model, memory_gb)
        try:
            yield LeaseToken(model=model, memory_gb=memory_gb)
        finally:
            await self.release(model, memory_gb)

    @abstractmethod
    async def acquire(self, model: str, memory_gb: float) -> None: ...

    @abstractmethod
    async def release(self, model: str, memory_gb: float) -> None: ...


class InMemoryModelLease(ModelLease):
    """Process-local lease for tests and single-worker dev."""

    def __init__(self) -> None:
        self._condition = asyncio.Condition()
        self._holder: str | None = None
        self._memory_gb = 0.0
        self._budget_gb: float | None = None

    def set_budget_gb(self, budget_gb: float) -> None:
        self._budget_gb = budget_gb

    async def acquire(self, model: str, memory_gb: float) -> None:
        async with self._condition:
            while self._holder is not None:
                await self._condition.wait()
            if self._budget_gb is not None and memory_gb > self._budget_gb:
                msg = f"Model {model} requires {memory_gb} GB, budget is {self._budget_gb} GB"
                raise ValueError(msg)
            self._holder = model
            self._memory_gb = memory_gb

    async def release(self, model: str, memory_gb: float) -> None:
        async with self._condition:
            if self._holder != model:
                msg = f"Lease held by {self._holder}, cannot release {model}"
                raise RuntimeError(msg)
            self._holder = None
            self._memory_gb = 0.0
            self._condition.notify_all()

    @property
    def holder(self) -> str | None:
        return self._holder


class RedisModelLease(ModelLease):
    """Cross-worker lease backed by Redis."""

    KEY = "assessgen:llm:lease"
    POLL_INTERVAL = 0.05

    def __init__(self, redis: Redis, *, ttl_seconds: int = 900, budget_gb: float = 11.0) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds
        self._budget_gb = budget_gb
        self._token: str | None = None

    async def acquire(self, model: str, memory_gb: float) -> None:
        if memory_gb > self._budget_gb:
            msg = f"Model {model} requires {memory_gb} GB, budget is {self._budget_gb} GB"
            raise ValueError(msg)
        token = f"{model}:{memory_gb}"
        while True:
            acquired = await self._redis.set(
                self.KEY,
                token,
                nx=True,
                ex=self._ttl_seconds,
            )
            if acquired:
                self._token = token
                return
            await asyncio.sleep(self.POLL_INTERVAL)

    async def release(self, model: str, memory_gb: float) -> None:
        token = f"{model}:{memory_gb}"
        if self._token != token:
            msg = f"Lease token mismatch: expected {self._token}, got {token}"
            raise RuntimeError(msg)
        await self._redis.delete(self.KEY)
        self._token = None


def build_model_lease(
    *,
    redis: Redis | None,
    budget_gb: float,
    ttl_seconds: int,
) -> ModelLease:
    if redis is None:
        lease = InMemoryModelLease()
        lease.set_budget_gb(budget_gb)
        return lease
    return RedisModelLease(redis, ttl_seconds=ttl_seconds, budget_gb=budget_gb)
