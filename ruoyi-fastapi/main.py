from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.websockets import WebSocketDisconnect

from assistant_server.auth import AuthenticationError, RuoYiAuthenticator
from assistant_server.config import Settings, load_local_env
from assistant_server.history import VoiceHistoryStore
from assistant_server.memory import MemoryManager
from assistant_server.realtime import (
    CapacityError,
    ConnectionLimiter,
    Metrics,
    RealtimeProxy,
)
from assistant_server.text_chat import TextChatError, TextChatService


BASE_DIR = Path(__file__).resolve().parent
APP_VERSION = "1.0.0"
load_local_env(BASE_DIR / ".env")
settings = Settings.from_env()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("assistant.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validation_errors = settings.validate()
    if validation_errors:
        raise RuntimeError("；".join(validation_errors))
    authenticator = RuoYiAuthenticator(settings)
    history = VoiceHistoryStore(settings)
    await history.start()
    memory = MemoryManager(settings, history)
    await memory.start()
    text_chat = TextChatService(settings)
    await text_chat.start()
    limiter = ConnectionLimiter(
        settings.max_connections, settings.max_connections_per_user
    )
    text_limiter = ConnectionLimiter(
        settings.text_max_connections, settings.text_max_connections_per_user
    )
    metrics = Metrics()
    app.state.authenticator = authenticator
    app.state.history = history
    app.state.memory = memory
    app.state.text_chat = text_chat
    app.state.limiter = limiter
    app.state.text_limiter = text_limiter
    app.state.metrics = metrics
    app.state.proxy = RealtimeProxy(settings, limiter, metrics, history, memory)
    logger.info(
        "assistant server ready: version=%s model=%s api_key=%s database=%s memory=%s text=%s",
        APP_VERSION,
        settings.dashscope_model,
        "configured" if settings.dashscope_api_key else "missing",
        "ready" if history.ready else "disabled",
        "ready" if memory.ready else "disabled",
        "ready" if text_chat.ready else "disabled",
    )
    try:
        yield
    finally:
        await text_chat.close()
        await memory.close()
        await history.close()
        await authenticator.close()


app = FastAPI(
    title="天猫智家实时语音服务",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=settings.allowed_origins != ("*",),
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def _websocket_origin_allowed(origin: str) -> bool:
    """兼容浏览器与 App WebView，同时保留常规网页的 Origin 白名单校验。

    HBuilderX App 运行时可能不发送 Origin，或使用 ``null``、``file://``、
    本机 WebView 地址。WebSocket 的首包仍必须携带有效登录令牌，因此这里
    仅放行这些原生容器来源，不会绕过账号鉴权。
    """
    if "*" in settings.allowed_origins or origin in settings.allowed_origins:
        return True
    normalized = (origin or "").lower().rstrip("/")
    if normalized in {"", "null", "file:"}:
        return True
    return normalized.startswith(("http://localhost:", "http://127.0.0.1:"))


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "name": "天猫智家 AI 助手服务",
        "version": APP_VERSION,
        "status": "running",
        "websocket": "/ws/v1/assistant",
        "text_websocket": "/ws/v1/text-chat",
        "docs": "/docs",
    }


@app.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def ready(request: Request) -> JSONResponse:
    configured = bool(settings.dashscope_api_key)
    return JSONResponse(
        status_code=200 if configured else 503,
        content={
            "status": "ready" if configured else "not_ready",
            "version": APP_VERSION,
            "dashscope_api_key": "configured" if configured else "missing",
            "active_sessions": request.app.state.limiter.active,
            "database": (
                "ready"
                if request.app.state.history.ready
                else "disabled"
                if not request.app.state.history.enabled
                else "not_ready"
            ),
            "database_dropped_events": request.app.state.history.dropped_events,
            "memory": (
                "ready"
                if request.app.state.memory.ready
                else "disabled"
                if not request.app.state.memory.enabled
                else "not_ready"
            ),
            "memory_dropped_jobs": request.app.state.memory.dropped_jobs,
            "text_chat": (
                "ready"
                if request.app.state.text_chat.ready
                else "disabled"
                if not request.app.state.text_chat.enabled
                else "not_ready"
            ),
            "active_text_sessions": request.app.state.text_limiter.active,
        },
    )


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics(request: Request) -> str:
    return request.app.state.metrics.render(request.app.state.limiter.active)


async def _authenticated_user(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    try:
        return await request.app.state.authenticator.authenticate(token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/api/v1/memories")
async def list_memories(request: Request) -> dict[str, Any]:
    user_id = await _authenticated_user(request)
    items = await request.app.state.memory.list_memories(user_id)
    return {"items": items, "count": len(items)}


@app.delete("/api/v1/memories/{memory_id}")
async def delete_memory(memory_id: int, request: Request) -> dict[str, bool]:
    user_id = await _authenticated_user(request)
    deleted = await request.app.state.memory.delete_memory(user_id, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="记忆不存在或已删除")
    return {"deleted": True}


@app.delete("/api/v1/memories")
async def clear_memories(request: Request) -> dict[str, int]:
    user_id = await _authenticated_user(request)
    deleted = await request.app.state.memory.clear_memories(user_id)
    return {"deleted": deleted}


@app.get("/api/v1/text-models")
async def text_models(request: Request) -> dict[str, Any]:
    await _authenticated_user(request)
    items = request.app.state.text_chat.model_catalog()
    return {"items": items, "count": len(items)}


@app.websocket("/ws/v1/assistant")
async def assistant_socket(websocket: WebSocket) -> None:
    origin = websocket.headers.get("origin", "")
    if not _websocket_origin_allowed(origin):
        await websocket.close(code=4403, reason="Origin not allowed")
        return
    await websocket.accept()
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10)
        if len(raw.encode("utf-8")) > settings.client_event_max_bytes:
            await websocket.close(code=1009, reason="client.hello too large")
            return
        hello = json.loads(raw)
    except (TimeoutError, WebSocketDisconnect, json.JSONDecodeError):
        await websocket.close(code=4400, reason="需要 client.hello")
        return
    if hello.get("type") != "client.hello":
        await websocket.close(code=4400, reason="首条消息必须是 client.hello")
        return
    try:
        user_id = await websocket.app.state.authenticator.authenticate(hello.get("token"))
    except AuthenticationError as exc:
        await websocket.send_json(
            {"type": "assistant.error", "code": "unauthorized", "message": str(exc)}
        )
        await websocket.close(code=4401)
        return
    client_id = str(hello.get("client_id") or "mobile")[:80]
    await websocket.app.state.proxy.run(websocket, user_id, client_id)


@app.websocket("/ws/v1/text-chat")
async def text_chat_socket(websocket: WebSocket) -> None:
    origin = websocket.headers.get("origin", "")
    if not _websocket_origin_allowed(origin):
        await websocket.close(code=4403, reason="Origin not allowed")
        return
    await websocket.accept()
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=15)
        if len(raw.encode("utf-8")) > settings.text_request_max_bytes:
            await websocket.send_json(
                {
                    "type": "text.error",
                    "code": "request_too_large",
                    "message": "文字对话请求过大，请新建对话或减少上下文",
                }
            )
            await websocket.close(code=1009)
            return
        hello = json.loads(raw)
        if hello.get("type") != "text.chat.start":
            raise TextChatError("invalid_request", "首条消息必须是 text.chat.start")
        user_id = await websocket.app.state.authenticator.authenticate(
            hello.get("token")
        )
        async with websocket.app.state.text_limiter.slot(user_id):
            websocket.app.state.metrics.inc("text_sessions_total")
            memory_context = ""
            try:
                memory_context = await asyncio.wait_for(
                    websocket.app.state.memory.get_context(user_id), timeout=3
                )
            except Exception:
                logger.exception("failed to load text chat memory: user_id=%s", user_id)
            result = await websocket.app.state.text_chat.stream_chat(
                websocket, hello, memory_context
            )
            memory_messages = list(result.transcript)
            memory_messages.append({"role": "assistant", "content": result.answer})
            websocket.app.state.memory.schedule_extraction(
                user_id, result.session_id, memory_messages
            )
    except AuthenticationError as exc:
        await _safe_ws_error(websocket, "unauthorized", str(exc))
    except CapacityError as exc:
        await _safe_ws_error(websocket, "capacity", str(exc))
    except TextChatError as exc:
        await _safe_ws_error(websocket, exc.code, exc.message)
    except (TimeoutError, json.JSONDecodeError):
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
        await websocket.send_json(
            {"type": "text.error", "code": code, "message": message}
        )
    except Exception:
        pass


if __name__ == "__main__":
    # Windows 上直接运行 `python main.py` 即可；生产环境可改用多 worker 进程。
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=False,
    )
