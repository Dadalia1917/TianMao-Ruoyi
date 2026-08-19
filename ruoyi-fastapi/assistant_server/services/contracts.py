from __future__ import annotations

from typing import Any, Protocol


class MemoryRepository(Protocol):
    """Persistence operations required by the memory service."""

    ready: bool

    async def fetch_all(
        self,
        statement: str,
        values: tuple[Any, ...] = (),
    ) -> tuple[tuple[Any, ...], ...]: ...

    async def execute_now(
        self,
        statement: str,
        values: tuple[Any, ...] = (),
    ) -> int: ...
