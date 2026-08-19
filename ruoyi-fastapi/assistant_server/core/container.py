from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass

from ..agent import HouseholdAgentService
from ..realtime import ConnectionLimiter, Metrics, RealtimeProxy
from ..services import MemoryManager, RuoYiAuthenticator, TextChatService, VoiceHistoryStore
from .config import Settings


@dataclass(frozen=True, slots=True)
class ApplicationServices:
    """Runtime dependencies owned by exactly one FastAPI worker."""

    authenticator: RuoYiAuthenticator
    history: VoiceHistoryStore
    memory: MemoryManager
    text_chat: TextChatService
    agent: HouseholdAgentService
    limiter: ConnectionLimiter
    text_limiter: ConnectionLimiter
    metrics: Metrics
    proxy: RealtimeProxy


@asynccontextmanager
async def create_service_scope(settings: Settings) -> AsyncIterator[ApplicationServices]:
    """Create services atomically and close them in reverse dependency order."""
    async with AsyncExitStack() as cleanup:
        authenticator = RuoYiAuthenticator(settings)
        cleanup.push_async_callback(authenticator.close)

        history = VoiceHistoryStore(settings)
        cleanup.push_async_callback(history.close)
        await history.start()

        memory = MemoryManager(settings, history)
        cleanup.push_async_callback(memory.close)
        text_chat = TextChatService(settings)
        cleanup.push_async_callback(text_chat.close)
        agent = HouseholdAgentService(settings)
        cleanup.push_async_callback(agent.close)

        # History must be ready before memory. The remaining services are
        # independent, so structured concurrency shortens startup and cancels
        # sibling initializers automatically if one fails.
        async with asyncio.TaskGroup() as startup_tasks:
            startup_tasks.create_task(memory.start(), name="start-memory")
            startup_tasks.create_task(text_chat.start(), name="start-text-chat")
            startup_tasks.create_task(agent.start(), name="start-agent")

        limiter = ConnectionLimiter(settings.max_connections, settings.max_connections_per_user)
        text_limiter = ConnectionLimiter(
            settings.text_max_connections,
            settings.text_max_connections_per_user,
        )
        metrics = Metrics()
        yield ApplicationServices(
            authenticator=authenticator,
            history=history,
            memory=memory,
            text_chat=text_chat,
            agent=agent,
            limiter=limiter,
            text_limiter=text_limiter,
            metrics=metrics,
            proxy=RealtimeProxy(settings, limiter, metrics, history, memory, agent),
        )
