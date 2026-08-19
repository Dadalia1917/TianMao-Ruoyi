from __future__ import annotations

import asyncio
import json
import time
from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from typing import Any

from fastapi import WebSocket


class CapacityError(Exception):
    pass


class SlowClientError(Exception):
    pass


def classify_upstream_connection_error(exc: BaseException) -> tuple[str, str]:
    """Convert DashScope connection failures into stable client-facing errors."""
    detail = str(exc).casefold()
    access_denied_markers = (
        "access denied",
        "account is in good standing",
        "http 401",
        "http 403",
        "unauthorized",
        "forbidden",
        "invalid api key",
        "invalid api-key",
    )
    if any(marker in detail for marker in access_denied_markers):
        return (
            "upstream_access_denied",
            "百炼未授权实时语音，请检查 API Key 所属账号状态、余额/欠费，以及 "
            "qwen3.5-omni-plus-realtime 模型权限。",
        )
    return (
        "upstream_unavailable",
        "千问实时语音暂时不可用，正在等待自动恢复。",
    )


class ConnectionLimiter:
    def __init__(self, global_limit: int, per_user_limit: int) -> None:
        self._global_limit = global_limit
        self._per_user_limit = per_user_limit
        self._active = 0
        self._per_user: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def slot(self, user_id: str):
        async with self._lock:
            if self._active >= self._global_limit:
                raise CapacityError("当前语音服务繁忙，请稍后再试")
            if self._per_user[user_id] >= self._per_user_limit:
                raise CapacityError("同一账号打开的语音会话过多")
            self._active += 1
            self._per_user[user_id] += 1
        try:
            yield
        finally:
            async with self._lock:
                self._active = max(0, self._active - 1)
                self._per_user[user_id] = max(0, self._per_user[user_id] - 1)
                if self._per_user[user_id] == 0:
                    self._per_user.pop(user_id, None)

    @property
    def active(self) -> int:
        return self._active


class Metrics:
    def __init__(self) -> None:
        self.started_at = time.time()
        self.counters: Counter[str] = Counter()

    def inc(self, name: str, amount: int = 1) -> None:
        self.counters[name] += amount

    def render(self, active: int) -> str:
        rows = [
            "# TYPE assistant_active_sessions gauge",
            f"assistant_active_sessions {active}",
            "# TYPE assistant_uptime_seconds gauge",
            f"assistant_uptime_seconds {max(0, time.time() - self.started_at):.0f}",
        ]
        for key, value in sorted(self.counters.items()):
            rows.extend((f"# TYPE assistant_{key} counter", f"assistant_{key} {value}"))
        return "\n".join(rows) + "\n"


class ClientWriter:
    """A bounded queue isolates a slow phone without unbounded server memory."""

    _STOP = object()

    def __init__(self, websocket: WebSocket, queue_size: int) -> None:
        self._websocket = websocket
        self._queue: asyncio.Queue[dict[str, Any] | object] = asyncio.Queue(queue_size)

    async def send(self, event: dict[str, Any]) -> None:
        try:
            await asyncio.wait_for(self._queue.put(event), timeout=1.0)
        except TimeoutError as exc:
            raise SlowClientError("客户端接收过慢") from exc

    async def run(self) -> None:
        while True:
            item = await self._queue.get()
            if item is self._STOP:
                return
            await self._websocket.send_text(
                json.dumps(item, ensure_ascii=False, separators=(",", ":"))
            )
