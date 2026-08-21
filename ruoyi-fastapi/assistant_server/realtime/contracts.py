from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from ..agent import AgentDecision, AgentRequest, IntentEntrypoint


class VoiceHistory(Protocol):
    """Voice persistence boundary used by the realtime gateway."""

    def start_session(
        self,
        *,
        session_id: str,
        user_key: str,
        ruoyi_user_id: int | None,
        client_id: str,
        client_ip: str,
        user_agent: str,
        model_name: str,
        voice_name: str,
    ) -> None: ...

    def activate_session(self, session_id: str, qwen_session_id: str) -> None: ...

    def add_message(
        self,
        *,
        session_id: str,
        sequence_no: int,
        role: str,
        content: str,
        qwen_item_id: str,
    ) -> None: ...

    def finish_session(
        self,
        *,
        session_id: str,
        status: str,
        duration_ms: int,
        message_count: int,
        input_text_chars: int,
        output_text_chars: int,
        close_reason: str,
    ) -> None: ...


class RealtimeMemory(Protocol):
    """Memory operations required on and immediately after the voice hot path."""

    ready: bool

    async def get_context(self, user_id: str | int) -> str: ...

    def schedule_extraction(
        self,
        user_id: str | int,
        session_id: str,
        messages: Iterable[dict[str, str]],
    ) -> None: ...

    def remember_recent_message(self, user_id: str | int, role: str, content: str) -> None: ...


class HouseholdPlanner(Protocol):
    """Planning boundary used by the realtime voice gateway."""

    def classify_entrypoint(self, transcript: str) -> IntentEntrypoint: ...

    async def plan(self, request: AgentRequest) -> AgentDecision: ...
