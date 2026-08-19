from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from websockets.asyncio.client import ClientConnection

from ..agent import AgentRequest
from ..agent.schemas import DecisionStatus
from ..core.config import Settings
from .contracts import HouseholdPlanner
from .protocol import SUBMIT_TIMEOUT_REPLY, classify_home_command_result, combine_home_commands
from .session import PendingHomeAction, WakeConversationState
from .transport import ClientWriter, Metrics

logger = logging.getLogger(__name__)


class HomeActionCoordinator:
    """Plan, confirm, submit, and reconcile low-risk household actions."""

    def __init__(
        self,
        *,
        settings: Settings,
        metrics: Metrics,
        agent: HouseholdPlanner,
    ) -> None:
        self.settings = settings
        self.metrics = metrics
        self.agent = agent

    async def submit(
        self,
        *,
        action: PendingHomeAction,
        writer: ClientWriter,
        upstream: ClientConnection,
        wake_state: WakeConversationState,
    ) -> None:
        wake_state.pending_home_action = None
        self.clear_pending_result(wake_state)
        wake_state.pending_home_execution_id = action.execution_id
        wake_state.home_result_timeout_task = wake_state.tasks.create(
            self._wait_for_result(
                execution_id=action.execution_id,
                upstream=upstream,
                writer=writer,
                wake_state=wake_state,
            ),
            name=f"home-result-{action.execution_id[:8]}",
        )
        await writer.send(
            {
                "type": "assistant.home_command.pending",
                "command": action.command,
                "commands": action.commands or [action.command],
                "execution_id": action.execution_id,
                "source": "household_agent_confirmed",
                "message": action.message,
                "rationale": action.rationale,
                "decision_basis": action.decision_basis,
                "evidence": action.evidence,
            }
        )
        self.metrics.inc("genie_provider_commands_total")
        await writer.send(
            {
                "type": "assistant.agent.notice",
                "status": "submitting",
                "message": "正在等待 T10S 返回真实提交结果",
            }
        )

    async def handle_result(
        self,
        *,
        event: dict[str, Any],
        upstream: ClientConnection,
        writer: ClientWriter,
        wake_state: WakeConversationState,
    ) -> None:
        execution_id = str(event.get("execution_id") or "")[:80]
        if not execution_id or execution_id != wake_state.pending_home_execution_id:
            self.metrics.inc("genie_provider_result_unmatched_total")
            logger.warning(
                "ignored unmatched home command result: expected=%s actual=%s",
                wake_state.pending_home_execution_id,
                execution_id,
            )
            return
        outcome, reply = classify_home_command_result(str(event.get("status") or ""))
        self.clear_pending_result(wake_state)
        wake_state.mode = "ending"
        self.metrics.inc(f"genie_provider_receipt_{outcome}_total")
        await writer.send(
            {
                "type": "assistant.agent.notice",
                "status": outcome,
                "message": reply,
                "execution_id": execution_id,
            }
        )
        await self.create_upstream_response(
            upstream,
            f"只用中文回答“{reply}”不得增加解释或其他文字。",
        )

    async def _wait_for_result(
        self,
        *,
        execution_id: str,
        upstream: ClientConnection,
        writer: ClientWriter,
        wake_state: WakeConversationState,
    ) -> None:
        try:
            await asyncio.sleep(self.settings.genie_provider_result_timeout_seconds)
            if wake_state.pending_home_execution_id != execution_id:
                return
            wake_state.pending_home_execution_id = ""
            wake_state.home_result_timeout_task = None
            wake_state.mode = "ending"
            self.metrics.inc("genie_provider_receipt_timeout_total")
            await writer.send(
                {
                    "type": "assistant.agent.notice",
                    "status": "timeout",
                    "message": SUBMIT_TIMEOUT_REPLY,
                    "execution_id": execution_id,
                }
            )
            await self.create_upstream_response(
                upstream,
                f"只用中文回答“{SUBMIT_TIMEOUT_REPLY}”不得增加解释或其他文字。",
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "failed to report home command result timeout: execution=%s",
                execution_id,
            )

    @staticmethod
    def clear_pending_result(wake_state: WakeConversationState) -> None:
        task = wake_state.home_result_timeout_task
        wake_state.home_result_timeout_task = None
        wake_state.pending_home_execution_id = ""
        if task and task is not asyncio.current_task() and not task.done():
            task.cancel()

    @staticmethod
    async def create_upstream_response(
        upstream: ClientConnection,
        instructions: str = "",
    ) -> None:
        event: dict[str, Any] = {"type": "response.create"}
        if instructions:
            event["response"] = {
                "modalities": ["text", "audio"],
                "instructions": instructions,
            }
        await upstream.send(json.dumps(event, ensure_ascii=False, separators=(",", ":")))

    @staticmethod
    async def delete_upstream_item(
        upstream: ClientConnection,
        item_id: str,
        wake_state: WakeConversationState,
    ) -> None:
        if not item_id:
            return
        await upstream.send(
            json.dumps(
                {"type": "conversation.item.delete", "item_id": item_id},
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        wake_state.conversation_item_ids.discard(item_id)

    async def clear_upstream_conversation(
        self,
        upstream: ClientConnection,
        wake_state: WakeConversationState,
    ) -> None:
        item_ids = tuple(wake_state.conversation_item_ids)
        wake_state.conversation_item_ids.clear()
        for item_id in item_ids:
            try:
                await upstream.send(
                    json.dumps(
                        {"type": "conversation.item.delete", "item_id": item_id},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                )
            except Exception:
                logger.debug("failed to clear Qwen conversation item %s", item_id)

    async def plan_and_dispatch(
        self,
        *,
        writer: ClientWriter,
        upstream: ClientConnection,
        wake_state: WakeConversationState,
        transcript: str,
        user_id: str,
        session_id: str,
        memory_context: str,
        confirmed_base_action: PendingHomeAction | None = None,
        submit_combined: bool = False,
    ) -> None:
        await writer.send(
            {
                "type": "assistant.agent.planning",
                "message": "正在结合家庭偏好与环境信息生成执行方案",
            }
        )
        try:
            decision = await asyncio.wait_for(
                self.agent.plan(
                    AgentRequest(
                        transcript=transcript,
                        user_id=user_id,
                        session_id=session_id,
                        location_name=self.settings.agent_location_name,
                        memory_context=memory_context,
                    )
                ),
                timeout=self.settings.agent_timeout_seconds,
            )
            self.metrics.inc(f"agent_{decision.status.value}_total")
            logger.info(
                "household agent decision: session=%s request=%s execution=%s status=%s device=%s command=%s evidence=%s",
                session_id,
                decision.request_id,
                decision.execution_id,
                decision.status.value,
                decision.action.device if decision.action else "",
                decision.action.command if decision.action else "",
                ",".join(item.kind for item in decision.evidence),
            )
            if wake_state.mode != "awake":
                self.metrics.inc("agent_stale_decisions_total")
                await writer.send(
                    {
                        "type": "assistant.agent.notice",
                        "status": "cancelled",
                        "message": "对话已结束，本次分析结果已丢弃，未执行家居操作。",
                    }
                )
                return
            if decision.status == DecisionStatus.EXECUTE and decision.action:
                evidence = [
                    {
                        "kind": item.kind,
                        "summary": item.summary,
                        "source": item.source,
                        "reliability": item.reliability,
                        "simulated": item.simulated,
                    }
                    for item in decision.evidence
                ]
                proposed_action = PendingHomeAction(
                    command=decision.action.command,
                    commands=[decision.action.command],
                    execution_id=decision.execution_id,
                    message=decision.user_message,
                    rationale=decision.rationale,
                    decision_basis=decision.decision_basis,
                    evidence=evidence,
                    transcript=transcript,
                )
                if confirmed_base_action is not None:
                    combined_action = PendingHomeAction(
                        command=combine_home_commands(
                            confirmed_base_action.command,
                            proposed_action.command,
                        ),
                        commands=list(
                            dict.fromkeys(
                                (confirmed_base_action.commands or [confirmed_base_action.command])
                                + (proposed_action.commands or [proposed_action.command])
                            )
                        )[:4],
                        execution_id=proposed_action.execution_id,
                        message=(
                            "已保留原方案并加入补充要求。当前拟执行："
                            f"{combine_home_commands(confirmed_base_action.command, proposed_action.command)}。"
                        )[:500],
                        rationale=(
                            f"{confirmed_base_action.rationale}；{proposed_action.rationale}"
                        )[:1000],
                        decision_basis=(
                            confirmed_base_action.decision_basis + proposed_action.decision_basis
                        )[:12],
                        evidence=(confirmed_base_action.evidence + proposed_action.evidence)[:24],
                        transcript=(f"{confirmed_base_action.transcript}；{transcript}")[:500],
                    )
                    if submit_combined:
                        await self.submit(
                            action=combined_action,
                            writer=writer,
                            upstream=upstream,
                            wake_state=wake_state,
                        )
                    else:
                        wake_state.pending_home_action = combined_action
                        await writer.send(
                            {
                                "type": "assistant.agent.notice",
                                "status": "awaiting_confirmation",
                                "message": combined_action.message,
                                "rationale": combined_action.rationale,
                                "decision_basis": combined_action.decision_basis,
                                "evidence": combined_action.evidence,
                            }
                        )
                        await self.create_upstream_response(
                            upstream,
                            "请明确告诉用户原方案已保留、补充动作已加入，并朗读以下合并方案后询问是否执行。"
                            f"只说这段内容：{combined_action.message}需要我执行这个合并方案吗？",
                        )
                    return
                wake_state.pending_home_action = proposed_action
                await writer.send(
                    {
                        "type": "assistant.agent.notice",
                        "status": "awaiting_confirmation",
                        "message": decision.user_message,
                        "rationale": decision.rationale,
                        "decision_basis": decision.decision_basis,
                        "evidence": evidence,
                    }
                )
                await self.create_upstream_response(
                    upstream,
                    "请完整、自然地朗读以下家庭状态分析和操作建议，然后询问用户是否执行。"
                    f"只说这段内容，不得声称已经执行：{decision.user_message} "
                    "需要我按这个方案处理吗？你也可以直接补充调整或换个方案。",
                )
                return
            # The Android ContentProvider may only be invoked by an explicit
            # EXECUTE decision.  Advice, clarification and non-applicable
            # results must never fall through to the old raw-command path.
            if confirmed_base_action is not None:
                wake_state.pending_home_action = confirmed_base_action
                message = f"补充要求暂时不能合并，原方案尚未执行。{decision.user_message}"
            else:
                message = decision.user_message
            await writer.send(
                {
                    "type": "assistant.agent.notice",
                    "status": decision.status.value,
                    "message": message,
                }
            )
            await self.create_upstream_response(
                upstream,
                f"请自然、完整地朗读这段结论，只说结论本身：{message}",
            )
            return
        except Exception:
            logger.exception(
                "household agent dispatch failed: session=%s",
                session_id,
            )
            self.metrics.inc("agent_failures_total")
            if confirmed_base_action is not None and wake_state.mode == "awake":
                wake_state.pending_home_action = confirmed_base_action
            await writer.send(
                {
                    "type": "assistant.agent.notice",
                    "status": "temporarily_unavailable",
                    "message": (
                        "补充要求暂时无法分析，原方案尚未执行。"
                        if confirmed_base_action is not None
                        else "智能决策暂时不可用，本次未执行家居操作，请稍后再试。"
                    ),
                }
            )
            await self.create_upstream_response(
                upstream,
                (
                    "只用中文回答“补充要求暂时无法分析，原方案尚未执行。你可以继续调整、执行原方案或取消。”"
                    if confirmed_base_action is not None
                    else "只用中文回答“智能决策暂时不可用，本次未执行家居操作，请稍后再试。”"
                ),
            )
            return
        finally:
            wake_state.home_plan_in_progress = False
