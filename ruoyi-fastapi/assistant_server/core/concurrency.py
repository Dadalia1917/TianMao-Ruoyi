from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any, TypeVar, cast

TaskResult = TypeVar("TaskResult")


class TaskSupervisor:
    """Own background tasks so failures are observed and shutdown is deterministic."""

    def __init__(self, *, label: str, logger: logging.Logger | None = None) -> None:
        self._label = label
        self._logger = logger or logging.getLogger(__name__)
        self._tasks: set[asyncio.Task[Any]] = set()

    def create(
        self,
        coroutine: Coroutine[Any, Any, TaskResult],
        *,
        name: str,
    ) -> asyncio.Task[TaskResult]:
        task = asyncio.create_task(coroutine, name=name)
        self._tasks.add(cast(asyncio.Task[Any], task))
        task.add_done_callback(self._task_finished)
        return task

    def _task_finished(self, task: asyncio.Task[Any]) -> None:
        self._tasks.discard(task)
        if task.cancelled():
            return
        try:
            error = task.exception()
        except asyncio.CancelledError:
            return
        if error is not None:
            self._logger.error(
                "%s background task failed: task=%s",
                self._label,
                task.get_name(),
                exc_info=(type(error), error, error.__traceback__),
            )

    @property
    def active_count(self) -> int:
        return len(self._tasks)

    def snapshot(self) -> tuple[asyncio.Task[Any], ...]:
        return tuple(self._tasks)

    async def cancel_all(self) -> None:
        current = asyncio.current_task()
        tasks = tuple(task for task in self._tasks if task is not current)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
