from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse

from ... import APP_VERSION
from ..dependencies import ServicesDep, SettingsDep

router = APIRouter(tags=["system"])


@router.get("/")
async def root() -> dict[str, Any]:
    return {
        "name": "天猫智家 AI 助手服务",
        "version": APP_VERSION,
        "status": "running",
        "websocket": "/ws/v1/assistant",
        "text_websocket": "/ws/v1/text-chat",
        "docs": "/docs",
    }


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(services: ServicesDep, settings: SettingsDep) -> JSONResponse:
    configured = bool(settings.dashscope_api_key)
    return JSONResponse(
        status_code=200 if configured else 503,
        content={
            "status": "ready" if configured else "not_ready",
            "version": APP_VERSION,
            "dashscope_api_key": "configured" if configured else "missing",
            "active_sessions": services.limiter.active,
            "database": (
                "ready"
                if services.history.ready
                else "disabled"
                if not services.history.enabled
                else "not_ready"
            ),
            "database_dropped_events": services.history.dropped_events,
            "memory": (
                "ready"
                if services.memory.ready
                else "disabled"
                if not services.memory.enabled
                else "not_ready"
            ),
            "memory_dropped_jobs": services.memory.dropped_jobs,
            "text_chat": (
                "ready"
                if services.text_chat.ready
                else "disabled"
                if not services.text_chat.enabled
                else "not_ready"
            ),
            "active_text_sessions": services.text_limiter.active,
            "household_agent": (
                "ready"
                if services.agent.ready
                else "policy_only"
                if services.agent.enabled
                else "disabled"
            ),
        },
    )


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics(services: ServicesDep) -> str:
    return services.metrics.render(services.limiter.active)
