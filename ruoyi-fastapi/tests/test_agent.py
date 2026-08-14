import asyncio
from datetime import datetime, timezone

import pytest

from assistant_server.agent import (
    AgentRequest,
    HouseholdAgentService,
    HouseholdStateUpdate,
)
from assistant_server.agent.state import HouseholdStateStore
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

    async def get_household_state(
        self, *, user_id: str, room: str, memory_context: str = ""
    ) -> Evidence:
        preferred = 25
        if "24度" in memory_context:
            preferred = 24
        return Evidence(
            kind="household_state",
            summary=f"{room}实测室温28℃，湿度68%，空调关闭，偏好{preferred}℃",
            source="test-home-assistant",
            observed_at=datetime.now(timezone.utc),
            reliability="high",
            data={
                "room": room,
                "indoor_temperature_c": 28,
                "indoor_humidity_percent": 68,
                "illuminance_lux": 20,
                "device_states": {"空调": {"power": False}},
                "time_period": "下午",
                "preferred_temperature_c": preferred,
            },
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
    assert decision.action.parameters["temperature_c"] == 24
    assert decision.action.command == "打开客厅空调并设置为24度"
    assert [item.kind for item in decision.evidence] == ["weather", "household_state"]
    assert "当前28.0℃" in decision.user_message
    assert len(decision.decision_basis) == 2


def test_light_uses_explicitly_simulated_environment(monkeypatch):
    decision = run_plan(
        build_agent(monkeypatch), AgentRequest(transcript="打开书房灯", user_id="1")
    )

    assert decision.status == DecisionStatus.EXECUTE
    assert decision.action is not None
    assert decision.action.parameters["brightness_percent"] == 80
    assert decision.action.command == "打开书房灯并调到80%亮度"
    environment = next(item for item in decision.evidence if item.kind == "environment")
    assert environment.simulated is True


def test_explicit_temperature_is_preserved(monkeypatch):
    decision = run_plan(
        build_agent(monkeypatch), AgentRequest(transcript="打开卧室空调到24度", user_id="1")
    )

    assert decision.status == DecisionStatus.EXECUTE
    assert decision.action is not None
    assert decision.action.parameters["temperature_c"] == 24
    assert decision.action.command == "打开卧室空调并设置为24度"


def test_implicit_heat_complaint_uses_complete_household_context(monkeypatch):
    decision = run_plan(
        build_agent(monkeypatch),
        AgentRequest(
            transcript="我有点热",
            user_id="1",
            memory_context="用户平时在家喜欢25度。",
        ),
    )

    assert decision.status == DecisionStatus.EXECUTE
    assert decision.action is not None
    assert decision.action.device == "空调"
    assert decision.action.room == "客厅"
    assert decision.action.command == "打开客厅空调并设置为25度"
    assert "湿度68" in decision.user_message
    assert "室外35" in decision.user_message
    assert agent_request_is_recognized(build_agent(monkeypatch), "我有点热")


def agent_request_is_recognized(agent: HouseholdAgentService, text: str) -> bool:
    return agent.might_be_home_request(text)


def test_household_state_merges_sensor_and_device_updates():
    async def scenario():
        store = HouseholdStateStore(ttl_seconds=300)
        await store.update(
            "1",
            "客厅",
            HouseholdStateUpdate(
                indoor_temperature_c=28,
                indoor_humidity_percent=68,
                source="test-sensor",
            ),
        )
        result = await store.update(
            "1",
            "客厅",
            HouseholdStateUpdate(
                device_states={"空调": {"power": False}},
                source="test-device-gateway",
            ),
        )
        assert result.indoor_temperature_c == 28
        assert result.indoor_humidity_percent == 68
        assert result.device_states["空调"]["power"] is False
        assert result.fresh is True
        assert await store.clear("1", "客厅") == 1
        assert await store.get("1", "客厅") is None

    asyncio.run(scenario())
