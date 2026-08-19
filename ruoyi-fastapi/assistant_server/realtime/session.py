from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..core.concurrency import TaskSupervisor


@dataclass(slots=True)
class PendingHomeAction:
    command: str
    commands: list[str]
    execution_id: str
    message: str
    rationale: str
    decision_basis: list[str]
    evidence: list[dict[str, Any]]
    transcript: str


@dataclass(slots=True)
class WakeConversationState:
    mode: str = "sleeping"
    response_active: bool = False
    conversation_item_ids: set[str] = field(default_factory=set)
    pending_home_action: PendingHomeAction | None = None
    home_plan_in_progress: bool = False
    pending_home_execution_id: str = ""
    home_result_timeout_task: asyncio.Task[None] | None = None
    client_playback_active: bool = False
    client_playback_completed_at: float = 0.0
    last_assistant_transcript: str = ""
    tasks: TaskSupervisor = field(default_factory=lambda: TaskSupervisor(label="realtime-session"))


@dataclass(slots=True)
class VoiceSessionStats:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_monotonic: float = field(default_factory=time.monotonic)
    status: str = "connecting"
    close_reason: str = ""
    sequence_no: int = 0
    message_count: int = 0
    input_text_chars: int = 0
    output_text_chars: int = 0
    messages: list[dict[str, str]] = field(default_factory=list)

    def record_message(self, role: str, content: str) -> int:
        self.sequence_no += 1
        self.message_count += 1
        if role == "user":
            self.input_text_chars += len(content)
        else:
            self.output_text_chars += len(content)
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > 240:
            del self.messages[: len(self.messages) - 240]
        return self.sequence_no

    @property
    def duration_ms(self) -> int:
        return max(0, round((time.monotonic() - self.started_monotonic) * 1000))
