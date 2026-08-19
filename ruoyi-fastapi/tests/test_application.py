from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from assistant_server import APP_VERSION
from assistant_server.application import create_app
from assistant_server.core import container as container_module
from assistant_server.core.config import Settings
from assistant_server.core.container import create_service_scope


def _test_settings(**overrides: object) -> Settings:
    settings = replace(
        Settings.from_env(),
        dashscope_api_key="test-api-key",
        database_enabled=False,
        memory_enabled=False,
        text_chat_enabled=False,
        agent_enabled=False,
        agent_state_redis_host="",
    )
    return replace(settings, **overrides)


@asynccontextmanager
async def _application_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client


def test_application_factory_registers_documented_routes() -> None:
    app = create_app(_test_settings())

    paths = set(app.openapi()["paths"])

    assert app.version == APP_VERSION
    assert {
        "/",
        "/health/live",
        "/health/ready",
        "/metrics",
        "/api/v1/memories",
        "/api/v1/text-models",
        "/api/v1/agent/capabilities",
        "/api/v1/agent/plan",
        "/api/v1/agent/household-state",
    } <= paths


def test_lifespan_publishes_services_and_health_state() -> None:
    app = create_app(_test_settings())

    async def scenario() -> None:
        async with _application_client(app) as client:
            root = await client.get("/")
            ready = await client.get("/health/ready")
            metrics = await client.get("/metrics")

            assert root.status_code == 200
            assert root.json()["version"] == APP_VERSION
            assert ready.status_code == 200
            expected_components = {
                "database": "disabled",
                "memory": "disabled",
                "text_chat": "disabled",
                "household_agent": "disabled",
            }
            payload = ready.json()
            assert {key: payload[key] for key in expected_components} == expected_components
            assert app.state.services.proxy is app.state.proxy
            assert "assistant_active_sessions 0" in metrics.text

    asyncio.run(scenario())


def test_http_authentication_error_has_stable_401_response() -> None:
    app = create_app(_test_settings())

    async def scenario() -> httpx.Response:
        async with _application_client(app) as client:
            return await client.get("/api/v1/memories")

    response = asyncio.run(scenario())
    assert response.status_code == 401
    assert response.json() == {"detail": "登录状态已失效，请重新登录"}


def test_configured_default_room_is_resolved_per_application() -> None:
    app = create_app(_test_settings(agent_default_room="书房"))

    async def scenario() -> httpx.Response:
        async with _application_client(app) as client:
            app.state.services.authenticator.authenticate = AsyncMock(return_value="7")
            return await client.get(
                "/api/v1/agent/household-state",
                headers={"Authorization": "Bearer test-token"},
            )

    response = asyncio.run(scenario())
    assert response.status_code == 200
    assert response.json()["room"] == "书房"


def test_partial_startup_is_cleaned_up(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    class FakeAuthenticator:
        def __init__(self, _settings: Settings) -> None:
            events.append("auth-created")

        async def close(self) -> None:
            events.append("auth-closed")

    class FailingHistory:
        def __init__(self, _settings: Settings) -> None:
            events.append("history-created")

        async def start(self) -> None:
            events.append("history-started")
            raise RuntimeError("startup failed")

        async def close(self) -> None:
            events.append("history-closed")

    monkeypatch.setattr(container_module, "RuoYiAuthenticator", FakeAuthenticator)
    monkeypatch.setattr(container_module, "VoiceHistoryStore", FailingHistory)
    app = create_app(_test_settings())

    async def scenario() -> None:
        with pytest.raises(RuntimeError, match="startup failed"):
            async with app.router.lifespan_context(app):
                pass

    asyncio.run(scenario())
    assert events == [
        "auth-created",
        "history-created",
        "history-started",
        "history-closed",
        "auth-closed",
    ]


def test_independent_services_start_concurrently(monkeypatch: pytest.MonkeyPatch) -> None:
    started: set[str] = set()
    release = asyncio.Event()

    def service_class(name: str):
        class ConcurrentService:
            enabled = True
            ready = False

            def __init__(self, *_args: object) -> None:
                self.ready = False

            async def start(self) -> None:
                started.add(name)
                if len(started) == 3:
                    release.set()
                await asyncio.wait_for(release.wait(), timeout=0.5)
                self.ready = True

            async def close(self) -> None:
                self.ready = False

        return ConcurrentService

    monkeypatch.setattr(container_module, "MemoryManager", service_class("memory"))
    monkeypatch.setattr(container_module, "TextChatService", service_class("text"))
    monkeypatch.setattr(container_module, "HouseholdAgentService", service_class("agent"))

    async def scenario() -> None:
        async with create_service_scope(_test_settings()) as services:
            assert services.memory.ready is True
            assert services.text_chat.ready is True
            assert services.agent.ready is True

    asyncio.run(scenario())
    assert started == {"memory", "text", "agent"}


def test_websocket_routes_remain_in_the_asgi_router() -> None:
    app = create_app(_test_settings())

    def collect_paths(router: object) -> set[str]:
        paths: set[str] = set()
        for route in getattr(router, "routes", ()):
            path = getattr(route, "path", "")
            if path:
                paths.add(path)
            nested = getattr(route, "original_router", None)
            if nested is not None:
                paths.update(collect_paths(nested))
        return paths

    websocket_paths = {path for path in collect_paths(app.router) if path.startswith("/ws/")}
    assert websocket_paths == {"/ws/v1/assistant", "/ws/v1/text-chat"}
