"""Model lease tests."""

import asyncio

import pytest
from app.infrastructure.llm.lease import InMemoryModelLease


@pytest.mark.asyncio
async def test_second_acquire_waits_for_release() -> None:
    lease = InMemoryModelLease()
    order: list[str] = []

    async def worker(name: str) -> None:
        await lease.acquire(f"model-{name}", 1.0)
        order.append(f"start-{name}")
        await asyncio.sleep(0.05)
        order.append(f"end-{name}")
        await lease.release(f"model-{name}", 1.0)

    first = asyncio.create_task(worker("a"))
    await asyncio.sleep(0.01)
    second = asyncio.create_task(worker("b"))
    await asyncio.gather(first, second)

    assert order.index("start-a") < order.index("end-a")
    assert order.index("end-a") < order.index("start-b")


@pytest.mark.asyncio
async def test_hold_context_manager_releases_on_exit() -> None:
    lease = InMemoryModelLease()
    async with lease.hold("qwen3.5:4b", 3.5):
        assert lease.holder == "qwen3.5:4b"
    assert lease.holder is None
