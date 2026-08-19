from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from ...core.config import Settings
from ...core.container import ApplicationServices
from ...realtime import CapacityError
from ...services import AuthenticationError, TextChatError

logger = logging.getLogger(__name__)
router = APIRouter()


def websocket_origin_allowed(origin: str, settings: Settings) -> bool:
    """Allow configured web origins plus trusted native WebView origins."""
    if "*" in settings.allowed_origins or origin in settings.allowed_origins:
        return True
    normalized = (origin or "").lower().rstrip("/")
    if normalized in {"", "null", "file:"}:
        return True
    return normalized.startswith(("http://localhost:", "http://127.0.0.1:"))


def _runtime(websocket: WebSocket) -> tuple[ApplicationServices, Settings]:
    return websocket.app.state.services, websocket.app.state.settings


async def _receive_json_object(
    websocket: WebSocket, *, receive_timeout: float, max_bytes: int
) -> dict[str, Any]:
    raw = await asyncio.wait_for(websocket.receive_text(), timeout=receive_timeout)
    if len(raw.encode("utf-8")) > max_bytes:
        raise ValueError("request_too_large")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise TypeError("JSON payload must be an object")
    return payload


@router.websocket("/ws/v1/assistant")
async def assistant_socket(websocket: WebSocket) -> None:
    services, settings = _runtime(websocket)
    origin = websocket.headers.get("origin", "")
    if not websocket_origin_allowed(origin, settings):
        await websocket.close(code=4403, reason="Origin not allowed")
        return
    await websocket.accept()
    try:
        hello = await _receive_json_object(
            websocket,
            receive_timeout=10,
            max_bytes=settings.client_event_max_bytes,
        )
    except ValueError as exc:
        if str(exc) == "request_too_large":
            await websocket.close(code=1009, reason="client.hello too large")
        else:
            await websocket.close(code=4400, reason="需要 client.hello")
        return
    except (TimeoutError, WebSocketDisconnect, json.JSONDecodeError, TypeError):
        await websocket.close(code=4400, reason="需要 client.hello")
        return
    if hello.get("type") != "client.hello":
        await websocket.close(code=4400, reason="首条消息必须是 client.hello")
        return
    try:
        user_id = await services.authenticator.authenticate(hello.get("token"))
    except AuthenticationError as exc:
        await websocket.send_json(
            {"type": "assistant.error", "code": "unauthorized", "message": str(exc)}
        )
        await websocket.close(code=4401)
        return
    client_id = str(hello.get("client_id") or "mobile")[:80]
    capabilities = hello.get("capabilities")
    genie_provider_available = bool(
        isinstance(capabilities, dict) and capabilities.get("genie_provider") is True
    )
    await services.proxy.run(
        websocket,
        user_id,
        client_id,
        genie_provider_available=genie_provider_available,
    )


@router.websocket("/ws/v1/text-chat")
async def text_chat_socket(websocket: WebSocket) -> None:
    services, settings = _runtime(websocket)
    origin = websocket.headers.get("origin", "")
    if not websocket_origin_allowed(origin, settings):
        await websocket.close(code=4403, reason="Origin not allowed")
        return
    await websocket.accept()
    try:
        hello = await _receive_json_object(
            websocket,
            receive_timeout=15,
            max_bytes=settings.text_request_max_bytes,
        )
        if hello.get("type") != "text.chat.start":
            raise TextChatError("invalid_request", "首条消息必须是 text.chat.start")
        user_id = await services.authenticator.authenticate(hello.get("token"))
        async with services.text_limiter.slot(user_id):
            services.metrics.inc("text_sessions_total")
            memory_context = ""
            try:
                memory_context = await asyncio.wait_for(
                    services.memory.get_context(user_id), timeout=3
                )
            except Exception:
                logger.exception("failed to load text chat memory: user_id=%s", user_id)
            result = await services.text_chat.stream_chat(websocket, hello, memory_context)
            memory_messages = list(result.transcript)
            memory_messages.append({"role": "assistant", "content": result.answer})
            services.memory.schedule_extraction(user_id, result.session_id, memory_messages)
    except AuthenticationError as exc:
        await _safe_ws_error(websocket, "unauthorized", str(exc))
    except CapacityError as exc:
        await _safe_ws_error(websocket, "capacity", str(exc))
    except TextChatError as exc:
        await _safe_ws_error(websocket, exc.code, exc.message)
    except ValueError as exc:
        if str(exc) == "request_too_large":
            await _safe_ws_error(
                websocket,
                "request_too_large",
                "文字对话请求过大，请新建对话或减少上下文",
            )
            await websocket.close(code=1009)
            return
        await _safe_ws_error(websocket, "invalid_request", "文字对话请求格式不正确")
    except (TimeoutError, json.JSONDecodeError, TypeError):
        await _safe_ws_error(websocket, "invalid_request", "文字对话请求格式不正确")
    except WebSocketDisconnect:
        return
    except Exception:
        logger.exception("unexpected text chat failure")
        await _safe_ws_error(websocket, "internal_error", "文字对话服务内部错误")
    finally:
        try:
            await websocket.close(code=1000)
        except Exception:
            pass


async def _safe_ws_error(websocket: WebSocket, code: str, message: str) -> None:
    try:
        await websocket.send_json({"type": "text.error", "code": code, "message": message})
    except Exception:
        pass
