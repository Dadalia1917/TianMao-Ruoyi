"""Realtime voice gateway and its stable public protocol helpers."""

from .gateway import RealtimeProxy
from .protocol import (
    build_session_update,
    classify_home_command_result,
    classify_home_confirmation,
    combine_home_commands,
    extract_confirmed_home_addition,
    extract_home_control_command,
    extract_pending_home_addition,
    extract_pending_home_replacement,
    extract_wake_request,
    is_conversation_exit,
    is_pending_replan_request,
    is_probable_assistant_echo,
    should_start_acoustic_relay,
)
from .session import PendingHomeAction, VoiceSessionStats, WakeConversationState
from .transport import (
    CapacityError,
    ConnectionLimiter,
    Metrics,
    SlowClientError,
    classify_upstream_connection_error,
)

__all__ = [
    "CapacityError",
    "ConnectionLimiter",
    "Metrics",
    "PendingHomeAction",
    "RealtimeProxy",
    "SlowClientError",
    "VoiceSessionStats",
    "WakeConversationState",
    "build_session_update",
    "classify_home_command_result",
    "classify_home_confirmation",
    "classify_upstream_connection_error",
    "combine_home_commands",
    "extract_confirmed_home_addition",
    "extract_home_control_command",
    "extract_pending_home_addition",
    "extract_pending_home_replacement",
    "extract_wake_request",
    "is_conversation_exit",
    "is_pending_replan_request",
    "is_probable_assistant_echo",
    "should_start_acoustic_relay",
]
