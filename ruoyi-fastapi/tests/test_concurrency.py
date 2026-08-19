from __future__ import annotations

import asyncio
import logging

from assistant_server.core.concurrency import TaskSupervisor


def test_task_supervisor_cancels_owned_tasks() -> None:
    async def scenario() -> tuple[int, bool]:
        supervisor = TaskSupervisor(label="test")
        started = asyncio.Event()
        stopped = asyncio.Event()

        async def worker() -> None:
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()

        supervisor.create(worker(), name="owned-worker")
        await started.wait()
        assert supervisor.active_count == 1
        await supervisor.cancel_all()
        return supervisor.active_count, stopped.is_set()

    active_count, stopped = asyncio.run(scenario())
    assert active_count == 0
    assert stopped is True


def test_task_supervisor_observes_background_failures(caplog) -> None:
    async def scenario() -> int:
        supervisor = TaskSupervisor(label="test-failure")

        async def fail() -> None:
            raise RuntimeError("background boom")

        task = supervisor.create(fail(), name="failing-worker")
        await asyncio.gather(task, return_exceptions=True)
        await asyncio.sleep(0)
        return supervisor.active_count

    with caplog.at_level(logging.ERROR):
        active_count = asyncio.run(scenario())

    assert active_count == 0
    assert "test-failure background task failed" in caplog.text
    assert "background boom" in caplog.text
