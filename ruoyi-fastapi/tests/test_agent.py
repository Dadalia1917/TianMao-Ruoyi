import asyncio
from datetime import datetime, timezone

import pytest

from assistant_server.agent import AgentRequest, HouseholdAgentService
from assistant_server.agent.schemas import DecisionStatus, Evidence
from assistant_server.config import Settings


class FakeDataTools:
    async def get_weather(self) -> Evidence:
        return Evidence(
            kind="weather",
            summary="无锡当前35℃",
            source="test-weather",
            observed_at=datetime.now(timezone.utc),
            reliability="high",
            data={"temperature_c": 35, "humidity_percent": 62},
        )

    async def get_environment(self) -> Evidence:
        return Evidence(
            kind="environment",
            summary="室内模拟照度20 lux",
            source="simulated-test-sensor",
            observed_at=datetime.now(timezone.utc),
            reliability="low",
            simulated=True,
            data={"illuminance_lux": 20},
        )


def build_agent(monkeypatch: pytest.MonkeyPatch) -> HouseholdAgentService:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "")
    agent = HouseholdAgentService(Settings.from_env())
    agent._data_tools = FakeDataTools()
    return agent


def run_plan(agent: HouseholdAgentService, request: AgentRequest):
    return asyncio.run(agent.plan(request))


def test_direct_low_risk_command_is_executable(monkeypatch):
    decision = run_plan(
        build_agent(monkeypatch), AgentRequest(transcript="关闭客厅窗帘", user_id="1")
    )

    assert decision.status == DecisionStatus.EXECUTE
    assert decision.action is not None
    assert decision.action.command == "关闭客厅窗帘"


def test_ambiguous_toggle_requires_clarification(monkeypatch):
    decision = run_plan(
        build_agent(monkeypatch), AgentRequest(transcript="帮我开关客厅灯", user_id="1")
    )

    assert decision.status == DecisionStatus.CLARIFY
    assert decision.action is None


def test_high_risk_device_is_blocked(monkeypatch):
    decision = run_plan(
        build_agent(monkeypatch), AgentRequest(transcript="打开大门门锁", user_id="1")
    )

    assert decision.status == DecisionStatus.BLOCKED
    assert decision.action is None


def test_device_status_question_is_not_executed(monkeypatch):
    decision = run_plan(
        build_agent(monkeypatch), AgentRequest(transcript="客厅空调开了吗", user_id="1")
    )

    assert decision.status == DecisionStatus.NOT_APPLICABLE


def test_air_conditioner_uses_weather_recommendation(monkeypatch):
    decision = run_plan(
        build_agent(monkeypatch),
        AgentRequest(
            transcript="打开客厅空调",
            user_id="1",
            memory_context="用户通常喜欢24度，但本次没有明确指定温度。",
        ),
    )

    assert decision.status == DecisionStatus.EXECUTE
    assert decision.action is not None
    assert decision.action.parameters["temperature_c"] == 27
    assert decision.action.command == "打开客厅空调并设置为27度"
    assert [item.kind for item in decision.evidence] == ["weather"]


def test_light_uses_explicitly_simulated_environment(monkeypatch):
    decision = run_plan(
        build_agent(monkeypatch), AgentRequest(transcript="打开书房灯", user_id="1")
    )

    assert decision.status == DecisionStatus.EXECUTE
    assert decision.action is not None
    assert decision.action.parameters["brightness_percent"] == 80
    assert decision.action.command == "打开书房灯并调到80%亮度"
    assert decision.evidence[0].simulated is True


def test_explicit_temperature_is_preserved(monkeypatch):
    decision = run_plan(
        build_agent(monkeypatch), AgentRequest(transcript="打开卧室空调到24度", user_id="1")
    )

    assert decision.status == DecisionStatus.EXECUTE
    assert decision.action is not None
    assert decision.action.parameters["temperature_c"] == 24
    assert decision.action.command == "打开卧室空调并设置为24度"
