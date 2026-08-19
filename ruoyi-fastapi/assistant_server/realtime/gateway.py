from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Coroutine
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from ..core.config import Settings
from .contracts import HouseholdPlanner, RealtimeMemory, VoiceHistory
from .home_actions import HomeActionCoordinator
from .protocol import (
    CANCEL_REPLY,
    CONFIRM_REPLY,
    EXIT_REPLY,
    WAKE_PHRASE,
    WAKE_REPLY,
    _safe_nonnegative_int,
    build_session_update,
    classify_home_confirmation,
    extract_confirmed_home_addition,
    extract_home_control_command,
    extract_pending_home_addition,
    extract_pending_home_replacement,
    extract_wake_request,
    is_conversation_exit,
    is_pending_replan_request,
    is_probable_assistant_echo,
)
from .session import VoiceSessionStats, WakeConversationState
from .transport import (
    CapacityError,
    ClientWriter,
    ConnectionLimiter,
    Metrics,
    SlowClientError,
    classify_upstream_connection_error,
)

logger = logging.getLogger(__name__)


def _track_background_task(
    wake_state: WakeConversationState,
    coroutine: Coroutine[Any, Any, None],
    *,
    name: str,
) -> None:
    """Keep fire-and-forget session work alive and cancellable on disconnect."""
    wake_state.tasks.create(coroutine, name=name)


class RealtimeProxy:
    def __init__(
        self,
        settings: Settings,
        limiter: ConnectionLimiter,
        metrics: Metrics,
        history: VoiceHistory,
        memory: RealtimeMemory,
        agent: HouseholdPlanner,
    ) -> None:
        self.settings = settings
        self.limiter = limiter
        self.metrics = metrics
        self.history = history
        self.memory = memory
        self.agent = agent
        self.home_actions = HomeActionCoordinator(
            settings=settings,
            metrics=metrics,
            agent=agent,
        )

    async def run(
        self,
        websocket: WebSocket,
        user_id: str,
        client_id: str,
        genie_provider_available: bool = False,
    ) -> None:
        if not self.settings.dashscope_api_key:
            await websocket.send_json(
                {
                    "type": "assistant.error",
                    "code": "missing_api_key",
                    "message": "服务端未配置 DASHSCOPE_API_KEY",
                }
            )
            await websocket.close(code=1011)
            return

        try:
            async with self.limiter.slot(user_id):
                self.metrics.inc("sessions_total")
                stats = VoiceSessionStats()
                ruoyi_user_id = int(user_id) if user_id.isdecimal() else None
                client_ip = websocket.client.host if websocket.client else ""
                self.history.start_session(
                    session_id=stats.session_id,
                    user_key=user_id[:64],
                    ruoyi_user_id=ruoyi_user_id,
                    client_id=client_id,
                    client_ip=client_ip,
                    user_agent=websocket.headers.get("user-agent", "")[:255],
                    model_name=self.settings.dashscope_model,
                    voice_name=self.settings.dashscope_voice,
                )
                memory_context = ""
                try:
                    memory_context = await asyncio.wait_for(
                        self.memory.get_context(user_id), timeout=3
                    )
                except Exception:
                    logger.exception("failed to load account memory: user_id=%s", user_id)
                try:
                    await self._run_upstream(
                        websocket,
                        client_id,
                        user_id,
                        stats,
                        memory_context,
                        genie_provider_available,
                    )
                finally:
                    if stats.status in {"connecting", "active"}:
                        stats.status = "closed"
                    self.history.finish_session(
                        session_id=stats.session_id,
                        status=stats.status,
                        duration_ms=stats.duration_ms,
                        message_count=stats.message_count,
                        input_text_chars=stats.input_text_chars,
                        output_text_chars=stats.output_text_chars,
                        close_reason=stats.close_reason,
                    )
                    self.memory.schedule_extraction(user_id, stats.session_id, stats.messages)
        except CapacityError as exc:
            self.metrics.inc("capacity_rejections_total")
            await websocket.send_json(
                {"type": "assistant.error", "code": "capacity", "message": str(exc)}
            )
            await websocket.close(code=1013)

    async def _run_upstream(
        self,
        websocket: WebSocket,
        client_id: str,
        user_id: str,
        stats: VoiceSessionStats,
        memory_context: str,
        genie_provider_available: bool,
    ) -> None:
        headers = {
            "Authorization": f"Bearer {self.settings.dashscope_api_key}",
            "X-DashScope-OmniRealtime": "true",
        }
        try:
            async with connect(
                self.settings.dashscope_ws_url,
                additional_headers=headers,
                open_timeout=12,
                close_timeout=5,
                ping_interval=20,
                ping_timeout=20,
                max_size=4 * 1024 * 1024,
                max_queue=32,
            ) as upstream:
                await self._configure_upstream(
                    websocket,
                    upstream,
                    client_id,
                    stats,
                    memory_context,
                    genie_provider_available,
                )
                writer = ClientWriter(websocket, self.settings.client_queue_size)
                wake_state = WakeConversationState()
                writer_task = asyncio.create_task(writer.run(), name=f"writer-{client_id}")
                client_task = asyncio.create_task(
                    self._client_to_upstream(
                        websocket,
                        upstream,
                        writer,
                        stats,
                        user_id,
                        wake_state,
                    ),
                    name=f"client-in-{client_id}",
                )
                upstream_task = asyncio.create_task(
                    self._upstream_to_client(
                        upstream,
                        writer,
                        stats,
                        user_id,
                        memory_context,
                        genie_provider_available,
                        wake_state,
                    ),
                    name=f"qwen-in-{client_id}",
                )
                tasks = {writer_task, client_task, upstream_task}
                rotate = False
                try:
                    async with asyncio.timeout(self.settings.upstream_rotate_seconds):
                        done, pending = await asyncio.wait(
                            tasks, return_when=asyncio.FIRST_COMPLETED
                        )
                        for task in done:
                            error = task.exception()
                            if error:
                                raise error
                        for task in pending:
                            task.cancel()
                except TimeoutError:
                    rotate = True
                finally:
                    self.home_actions.clear_pending_result(wake_state)
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    await wake_state.tasks.cancel_all()
                if rotate:
                    stats.status = "rotated"
                    stats.close_reason = "upstream_rotation"
                    self.metrics.inc("session_rotations_total")
                    await websocket.send_json(
                        {
                            "type": "assistant.session.rotating",
                            "message": "正在续接长期待命会话",
                        }
                    )
        except (ConnectionClosed, InvalidStatus, OSError, TimeoutError) as exc:
            stats.status = "failed"
            error_code, user_message = classify_upstream_connection_error(exc)
            stats.close_reason = error_code
            self.metrics.inc("upstream_errors_total")
            logger.warning("DashScope realtime connection failed: %s", exc)
            try:
                await websocket.send_json(
                    {
                        "type": "assistant.error",
                        "code": error_code,
                        "message": user_message,
                    }
                )
            except Exception:
                pass
        except RuntimeError as exc:
            stats.status = "failed"
            stats.close_reason = str(exc)[:255]
            self.metrics.inc("upstream_errors_total")
            logger.warning("DashScope realtime initialization failed: %s", exc)
            try:
                await websocket.send_json(
                    {
                        "type": "assistant.error",
                        "code": "upstream_initialization_failed",
                        "message": str(exc),
                    }
                )
            except Exception:
                pass
        except (WebSocketDisconnect, SlowClientError):
            stats.status = "closed"
            stats.close_reason = "client_disconnected"
            return
        except Exception as exc:
            stats.status = "failed"
            stats.close_reason = type(exc).__name__
            self.metrics.inc("session_errors_total")
            logger.exception("unexpected realtime session failure")
            try:
                await websocket.send_json(
                    {
                        "type": "assistant.error",
                        "code": "internal_error",
                        "message": "实时语音服务内部错误",
                    }
                )
            except Exception:
                pass

    async def _configure_upstream(
        self,
        websocket: WebSocket,
        upstream: ClientConnection,
        client_id: str,
        stats: VoiceSessionStats,
        memory_context: str,
        genie_provider_available: bool,
    ) -> None:
        first = await asyncio.wait_for(upstream.recv(), timeout=10)
        first_event = json.loads(first)
        if first_event.get("type") == "error":
            raise RuntimeError(first_event.get("error", {}).get("message", "千问连接失败"))
        qwen_session_id = str((first_event.get("session") or {}).get("id") or "")

        await upstream.send(
            json.dumps(
                build_session_update(
                    self.settings,
                    memory_context,
                    genie_provider_available=genie_provider_available,
                ),
                # App capability is negotiated in client.hello. A normal browser
                # therefore never receives instructions that imply local control.
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )

        for _ in range(8):
            raw = await asyncio.wait_for(upstream.recv(), timeout=10)
            event = json.loads(raw)
            if event.get("type") == "error":
                message = event.get("error", {}).get("message") or "千问会话配置失败"
                raise RuntimeError(message)
            if event.get("type") == "session.updated":
                stats.status = "active"
                self.history.activate_session(stats.session_id, qwen_session_id)
                await websocket.send_json(
                    {
                        "type": "assistant.session.ready",
                        "client_id": client_id,
                        "sample_rate_in": 16000,
                        "sample_rate_out": 24000,
                        "continuous": True,
                        "wake_state": "sleeping",
                        "wake_phrase": WAKE_PHRASE,
                        "rotate_seconds": self.settings.upstream_rotate_seconds,
                        "memory_enabled": self.memory.ready,
                    }
                )
                return
        raise RuntimeError("千问会话初始化未完成")

    async def _client_to_upstream(
        self,
        websocket: WebSocket,
        upstream: ClientConnection,
        writer: ClientWriter,
        stats: VoiceSessionStats,
        user_id: str,
        wake_state: WakeConversationState,
    ) -> None:
        allowed = {
            "input_audio_buffer.append",
            "input_audio_buffer.commit",
            "input_audio_buffer.clear",
            "response.cancel",
        }
        window_started = time.monotonic()
        window_bytes = 0
        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                return
            if len(raw.encode("utf-8")) > self.settings.client_event_max_bytes:
                self.metrics.inc("oversized_events_total")
                await websocket.close(code=1009)
                return
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            event_type = event.get("type")
            if event_type == "ping":
                continue
            if event_type == "client.playback.started":
                wake_state.client_playback_active = True
                wake_state.client_playback_completed_at = 0.0
                self.metrics.inc("client_playback_started_total")
                continue
            if event_type == "client.playback.done":
                wake_state.client_playback_active = False
                wake_state.client_playback_completed_at = time.monotonic()
                self.metrics.inc("client_playback_done_total")
                continue
            if event_type == "client.audio_diagnostics":
                processor = str(event.get("processor") or "unknown")
                if processor not in {"audio_worklet", "script_processor"}:
                    processor = "unknown"
                dropped_frames = _safe_nonnegative_int(event.get("dropped_frames"))
                self.metrics.inc(f"capture_{processor}_reports_total")
                if dropped_frames:
                    self.metrics.inc("capture_backpressure_reports_total")
                logger.info(
                    "audio capture diagnostics: session=%s user=%s phase=%s processor=%s track_rate=%s context_rate=%s channels=%s echo=%s noise=%s agc=%s rms_x10000=%s peak_x10000=%s gain_x100=%s music=%s frames=%s dropped=%s buffered=%s",
                    stats.session_id,
                    user_id,
                    str(event.get("phase") or "")[:20],
                    processor,
                    _safe_nonnegative_int(event.get("track_sample_rate")),
                    _safe_nonnegative_int(event.get("context_sample_rate")),
                    _safe_nonnegative_int(event.get("channel_count")),
                    bool(event.get("echo_cancellation")),
                    bool(event.get("noise_suppression")),
                    bool(event.get("auto_gain_control")),
                    _safe_nonnegative_int(event.get("input_rms_x10000")),
                    _safe_nonnegative_int(event.get("input_peak_x10000")),
                    _safe_nonnegative_int(event.get("software_gain_x100")),
                    bool(event.get("music_playback_active")),
                    _safe_nonnegative_int(event.get("frames")),
                    dropped_frames,
                    _safe_nonnegative_int(event.get("socket_buffered_bytes")),
                )
                continue
            if event_type == "assistant.home_command.result":
                status = str(event.get("status") or "unknown")[:40]
                execution_id = str(event.get("execution_id") or "")[:80]
                self.metrics.inc(f"genie_provider_result_{status}_total")
                logger.info(
                    "home command result: session=%s user=%s execution=%s status=%s message=%s",
                    stats.session_id,
                    user_id,
                    execution_id,
                    status,
                    str(event.get("message") or "")[:200],
                )
                await self.home_actions.handle_result(
                    event=event,
                    upstream=upstream,
                    writer=writer,
                    wake_state=wake_state,
                )
                continue
            if event_type not in allowed:
                continue
            if event_type == "input_audio_buffer.append":
                audio = event.get("audio")
                if not isinstance(audio, str) or not audio:
                    continue
                now = time.monotonic()
                if now - window_started >= 1.0:
                    window_started, window_bytes = now, 0
                window_bytes += len(audio)
                # 16 kHz mono PCM is ~43 KB/s after base64. Leave room for jitter.
                if window_bytes > 192_000:
                    self.metrics.inc("audio_rate_limit_total")
                    continue
                self.metrics.inc("audio_events_total")
            await upstream.send(json.dumps(event, ensure_ascii=False, separators=(",", ":")))

    async def _upstream_to_client(
        self,
        upstream: ClientConnection,
        writer: ClientWriter,
        stats: VoiceSessionStats,
        user_id: str,
        memory_context: str,
        genie_provider_available: bool,
        wake_state: WakeConversationState,
    ) -> None:
        seen_transcripts: set[tuple[str, str, str]] = set()
        seen_user_turns: set[tuple[str, str]] = set()
        seen_home_commands: set[tuple[str, str]] = set()
        async for raw in upstream:
            try:
                event = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            event_type = event.get("type", "")
            if event_type == "conversation.item.input_audio_transcription.failed":
                self.metrics.inc("input_audio_transcription_failed_total")

            item = event.get("item") if isinstance(event.get("item"), dict) else {}
            created_item_id = str(item.get("id") or event.get("item_id") or "")
            if event_type == "conversation.item.created" and created_item_id:
                wake_state.conversation_item_ids.add(created_item_id)

            role = ""
            content = ""
            if event_type == "conversation.item.input_audio_transcription.completed":
                qwen_item_id = str(event.get("item_id") or event.get("event_id") or "")
                original_content = str(event.get("transcript") or "").strip()
                # DashScope normally supplies a stable item id.  Only dedupe
                # when that id exists: using the transcript alone would make a
                # legitimate repeated command such as “开灯” disappear.
                if qwen_item_id:
                    user_turn_key = (qwen_item_id, original_content)
                    if user_turn_key in seen_user_turns:
                        continue
                    seen_user_turns.add(user_turn_key)

                if self._should_filter_assistant_echo(wake_state, original_content):
                    await self.home_actions.delete_upstream_item(upstream, qwen_item_id, wake_state)
                    self.metrics.inc("assistant_echo_transcripts_filtered_total")
                    await writer.send(
                        {
                            "type": "assistant.audio.filtered",
                            "reason": "probable_assistant_echo",
                        }
                    )
                    continue

                if wake_state.mode == "sleeping":
                    woke, wake_request = extract_wake_request(original_content)
                    if not woke:
                        await self.home_actions.delete_upstream_item(
                            upstream, qwen_item_id, wake_state
                        )
                        self.metrics.inc("dormant_utterances_ignored_total")
                        continue
                    wake_state.mode = "awake"
                    await writer.send(
                        {
                            "type": "assistant.wake_state",
                            "state": "awake",
                            "wake_phrase": WAKE_PHRASE,
                        }
                    )
                    self.metrics.inc("wake_phrase_matches_total")
                    content = wake_request
                    if not content:
                        await self.home_actions.create_upstream_response(
                            upstream,
                            f"只用中文回答“{WAKE_REPLY}”不得增加称呼、解释或其他文字。",
                        )
                        continue
                elif wake_state.mode == "ending":
                    await self.home_actions.delete_upstream_item(upstream, qwen_item_id, wake_state)
                    continue
                else:
                    content = original_content

                role = "user"
                event = dict(event)
                event["transcript"] = content
                await writer.send(event)

                if is_conversation_exit(content):
                    wake_state.pending_home_action = None
                    wake_state.home_plan_in_progress = False
                    self.home_actions.clear_pending_result(wake_state)
                    wake_state.mode = "ending"
                    await self.home_actions.create_upstream_response(
                        upstream,
                        f"只用中文回答“{EXIT_REPLY}”不得增加称呼、解释或其他文字。",
                    )
                    self.metrics.inc("conversation_exit_requests_total")
                    continue

                if wake_state.pending_home_action is not None:
                    restart_woke, restart_request = extract_wake_request(content)
                    if restart_woke:
                        wake_state.pending_home_action = None
                        self.home_actions.clear_pending_result(wake_state)
                        if restart_request and is_conversation_exit(restart_request):
                            wake_state.mode = "ending"
                            await self.home_actions.create_upstream_response(
                                upstream,
                                f"只用中文回答“{EXIT_REPLY}”不得增加称呼、解释或其他文字。",
                            )
                            self.metrics.inc("conversation_exit_requests_total")
                            continue
                        if not restart_request or is_pending_replan_request(restart_request):
                            await self.home_actions.create_upstream_response(
                                upstream,
                                "只用中文回答“好的，我们重新开始。请告诉我现在需要什么。”不得增加其他文字。",
                            )
                            continue
                        content = restart_request

                if wake_state.pending_home_action is not None:
                    action = wake_state.pending_home_action
                    confirmed_addition = extract_confirmed_home_addition(content)
                    pending_addition = (
                        "" if confirmed_addition else extract_pending_home_addition(content)
                    )
                    replacement = extract_pending_home_replacement(content)
                    confirmation = classify_home_confirmation(content)
                    if confirmed_addition or pending_addition:
                        addition = confirmed_addition or pending_addition
                        wake_state.pending_home_action = None
                        self.home_actions.clear_pending_result(wake_state)
                        if wake_state.home_plan_in_progress:
                            wake_state.pending_home_action = action
                            await self.home_actions.create_upstream_response(
                                upstream,
                                "只用中文回答“我正在分析补充要求，请稍等。”不得增加其他文字。",
                            )
                        else:
                            wake_state.home_plan_in_progress = True
                            _track_background_task(
                                wake_state,
                                self.home_actions.plan_and_dispatch(
                                    writer=writer,
                                    upstream=upstream,
                                    wake_state=wake_state,
                                    transcript=addition,
                                    user_id=user_id,
                                    session_id=stats.session_id,
                                    memory_context=memory_context,
                                    confirmed_base_action=action,
                                    submit_combined=bool(confirmed_addition),
                                ),
                                name=f"home-agent-addition-{stats.session_id[:8]}",
                            )
                    elif replacement:
                        wake_state.pending_home_action = None
                        if wake_state.home_plan_in_progress:
                            wake_state.pending_home_action = action
                            await self.home_actions.create_upstream_response(
                                upstream,
                                "只用中文回答“我正在按你的要求替换方案，请稍等。”不得增加其他文字。",
                            )
                        else:
                            wake_state.home_plan_in_progress = True
                            _track_background_task(
                                wake_state,
                                self.home_actions.plan_and_dispatch(
                                    writer=writer,
                                    upstream=upstream,
                                    wake_state=wake_state,
                                    transcript=replacement,
                                    user_id=user_id,
                                    session_id=stats.session_id,
                                    memory_context=memory_context,
                                ),
                                name=f"home-agent-replace-{stats.session_id[:8]}",
                            )
                    elif confirmation == "confirm":
                        await self.home_actions.submit(
                            action=action,
                            writer=writer,
                            upstream=upstream,
                            wake_state=wake_state,
                        )
                    elif confirmation == "cancel":
                        wake_state.pending_home_action = None
                        wake_state.mode = "ending"
                        await self.home_actions.create_upstream_response(
                            upstream,
                            f"只用中文回答“{CANCEL_REPLY}”不得增加解释或其他文字。",
                        )
                    elif is_pending_replan_request(content):
                        wake_state.pending_home_action = None
                        if wake_state.home_plan_in_progress:
                            wake_state.pending_home_action = action
                            await self.home_actions.create_upstream_response(
                                upstream,
                                "只用中文回答“我正在分析新的方案，请稍等。”不得增加其他文字。",
                            )
                        else:
                            wake_state.home_plan_in_progress = True
                            replan_transcript = (
                                f"{action.transcript}。请换一个与上一方案不同的低风险方案，"
                                f"上一方案是：{action.command}"
                            )
                            _track_background_task(
                                wake_state,
                                self.home_actions.plan_and_dispatch(
                                    writer=writer,
                                    upstream=upstream,
                                    wake_state=wake_state,
                                    transcript=replan_transcript,
                                    user_id=user_id,
                                    session_id=stats.session_id,
                                    memory_context=memory_context,
                                ),
                                name=f"home-agent-replan-{stats.session_id[:8]}",
                            )
                    elif self.agent.might_be_home_request(content):
                        wake_state.pending_home_action = None
                        if wake_state.home_plan_in_progress:
                            wake_state.pending_home_action = action
                            await self.home_actions.create_upstream_response(
                                upstream,
                                "只用中文回答“我正在分析新的要求，请稍等。”不得增加其他文字。",
                            )
                        else:
                            wake_state.home_plan_in_progress = True
                            _track_background_task(
                                wake_state,
                                self.home_actions.plan_and_dispatch(
                                    writer=writer,
                                    upstream=upstream,
                                    wake_state=wake_state,
                                    transcript=content,
                                    user_id=user_id,
                                    session_id=stats.session_id,
                                    memory_context=memory_context,
                                    confirmed_base_action=action,
                                    submit_combined=False,
                                ),
                                name=f"home-agent-implicit-addition-{stats.session_id[:8]}",
                            )
                    else:
                        await self.home_actions.create_upstream_response(
                            upstream,
                            f"只用中文回答“{CONFIRM_REPLY}”不得增加解释或其他文字。",
                        )
                    continue

                home_command = extract_home_control_command(content)
                is_home_request = self.agent.might_be_home_request(content)
                is_advice_only_request = self.agent.might_be_advice_only_request(content)
                home_key = (qwen_item_id, content)
                if (
                    wake_state.mode == "awake"
                    and is_home_request
                    and home_key not in seen_home_commands
                    and (
                        is_advice_only_request
                        or (self.settings.genie_provider_enabled and genie_provider_available)
                    )
                ):
                    seen_home_commands.add(home_key)
                    if wake_state.home_plan_in_progress:
                        await self.home_actions.create_upstream_response(
                            upstream,
                            "只用中文回答“我正在分析家里的情况，请稍等。”不得增加其他文字。",
                        )
                    else:
                        wake_state.home_plan_in_progress = True
                        _track_background_task(
                            wake_state,
                            self.home_actions.plan_and_dispatch(
                                writer=writer,
                                upstream=upstream,
                                wake_state=wake_state,
                                transcript=content,
                                user_id=user_id,
                                session_id=stats.session_id,
                                memory_context=memory_context,
                            ),
                            name=f"home-agent-{stats.session_id[:8]}",
                        )
                    continue
                elif (
                    wake_state.mode == "awake"
                    and home_command
                    and home_key not in seen_home_commands
                    and self.settings.acoustic_relay_enabled
                ):
                    seen_home_commands.add(home_key)
                    await writer.send(
                        {
                            "type": "assistant.acoustic_relay.pending",
                            "wake_phrase": self.settings.acoustic_relay_wake_phrase,
                            "message": "正在把家居指令转达给附近的天猫精灵",
                        }
                    )
                    self.metrics.inc("acoustic_relays_total")
                else:
                    await self.home_actions.create_upstream_response(upstream)
            elif event_type == "response.audio_transcript.done":
                await writer.send(event)
                role = "assistant"
                content = str(event.get("transcript") or "").strip()
            elif event_type == "response.text.done":
                await writer.send(event)
                role = "assistant"
                content = str(event.get("text") or "").strip()
            else:
                await writer.send(event)

            if event_type == "response.created":
                wake_state.response_active = True
            elif event_type == "response.done":
                wake_state.response_active = False
                if wake_state.mode == "ending":
                    wake_state.mode = "sleeping"
                    wake_state.pending_home_action = None
                    wake_state.home_plan_in_progress = False
                    self.home_actions.clear_pending_result(wake_state)
                    await writer.send(
                        {
                            "type": "assistant.wake_state",
                            "state": "sleeping",
                            "wake_phrase": WAKE_PHRASE,
                            "reason": "conversation_ended",
                            "message": f"对话已结束，请说“{WAKE_PHRASE}”再次唤醒",
                        }
                    )
                    await self.home_actions.clear_upstream_conversation(upstream, wake_state)
            if role and content:
                if role == "assistant":
                    wake_state.last_assistant_transcript = content
                qwen_item_id = str(
                    event.get("item_id") or event.get("response_id") or event.get("event_id") or ""
                )
                dedupe_key = (role, qwen_item_id, content)
                if dedupe_key not in seen_transcripts:
                    seen_transcripts.add(dedupe_key)
                    sequence_no = stats.record_message(role, content)
                    self.memory.remember_recent_message(user_id, role, content)
                    self.history.add_message(
                        session_id=stats.session_id,
                        sequence_no=sequence_no,
                        role=role,
                        content=content,
                        qwen_item_id=qwen_item_id,
                    )

            if event_type == "error":
                self.metrics.inc("qwen_errors_total")

    def _should_filter_assistant_echo(
        self,
        wake_state: WakeConversationState,
        transcript: str,
    ) -> bool:
        if wake_state.client_playback_active:
            return True
        completed_at = wake_state.client_playback_completed_at
        if completed_at <= 0:
            return False
        if time.monotonic() - completed_at > self.settings.realtime_echo_guard_seconds:
            return False
        return is_probable_assistant_echo(
            transcript,
            wake_state.last_assistant_transcript,
        )
