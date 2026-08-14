from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RiskLevel(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"


class ActionLevel(str, Enum):
    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"


class DecisionStatus(str, Enum):
    EXECUTE = "execute"
    ADVISE = "advise"
    CLARIFY = "clarify"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(max_length=40)
    summary: str = Field(max_length=500)
    source: str = Field(max_length=200)
    observed_at: datetime
    reliability: Literal["high", "medium", "low", "unavailable"]
    simulated: bool = False
    data: dict[str, Any] = Field(default_factory=dict)


class DeviceAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str = Field(min_length=1, max_length=120)
    device: str = Field(min_length=1, max_length=40)
    room: str = Field(default="", max_length=40)
    action: str = Field(min_length=1, max_length=30)
    parameters: dict[str, Any] = Field(default_factory=dict)
    action_level: ActionLevel = ActionLevel.A1
    risk_level: RiskLevel = RiskLevel.L1
    requires_confirmation: bool = False


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transcript: str = Field(min_length=1, max_length=500)
    user_id: str = Field(default="anonymous", max_length=80)
    session_id: str = Field(default="", max_length=80)
    location_name: str | None = Field(default=None, max_length=80)
    memory_context: str = Field(default="", max_length=6000)
    dry_run: bool = False


class AgentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    execution_id: str
    status: DecisionStatus
    user_message: str = Field(max_length=500)
    rationale: str = Field(default="", max_length=1000)
    decision_basis: list[str] = Field(default_factory=list, max_length=12)
    action: DeviceAction | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    used_function_calling: bool = False
    policy_version: str = "household-agent-1.1"
    created_at: datetime


class HouseholdStateUpdate(BaseModel):
    """Partial live state reported by Home Assistant, sensors or the Android client."""

    model_config = ConfigDict(extra="forbid")

    indoor_temperature_c: float | None = Field(default=None, ge=-20, le=60)
    indoor_humidity_percent: float | None = Field(default=None, ge=0, le=100)
    illuminance_lux: float | None = Field(default=None, ge=0, le=500_000)
    occupancy: bool | None = None
    device_states: dict[str, dict[str, Any]] = Field(default_factory=dict)
    source: str = Field(default="sensor_gateway", min_length=1, max_length=80)
    observed_at: datetime | None = None


class HouseholdStateSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    room: str
    indoor_temperature_c: float | None = None
    indoor_humidity_percent: float | None = None
    illuminance_lux: float | None = None
    occupancy: bool | None = None
    device_states: dict[str, dict[str, Any]] = Field(default_factory=dict)
    source: str
    observed_at: datetime
    received_at: datetime
    fresh: bool
    expires_in_seconds: int


class ModelPlan(BaseModel):
    """Strict payload accepted from the model's submit_home_plan tool."""

    model_config = ConfigDict(extra="forbid")

    command: str = Field(min_length=1, max_length=120)
    device: str = Field(min_length=1, max_length=40)
    room: str = Field(default="", max_length=40)
    action: str = Field(min_length=1, max_length=30)
    user_message: str = Field(min_length=1, max_length=300)
    rationale: str = Field(min_length=1, max_length=600)
    parameters: dict[str, Any] = Field(default_factory=dict)
