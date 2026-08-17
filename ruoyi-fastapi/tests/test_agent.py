import asyncio
from datetime import datetime, timezone

import pytest

from assistant_server.agent import (
    AgentRequest,
    HouseholdAgentService,
    HouseholdStateUpdate,
)
from assistant_server.agent.state import HouseholdStateStore
from assistant_server.agent.handlers import IntentContext
from assistant_server.agent.schemas import DecisionStatus, Evidence, RiskLevel
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
                "field_sources": {"illuminance_lux": "live_sensor"},
                "device_states": {"空调": {"power": False}},
                "time_period": "下午",
                "preferred_temperature_c": preferred,
            },
        )


class CoolDataTools(FakeDataTools):
    async def get_household_state(
        self, *, user_id: str, room: str, memory_context: str = ""
    ) -> Evidence:
        item = await super().get_household_state(
            user_id=user_id,
            room=room,
            memory_context=memory_context,
        )
        item.data["indoor_temperature_c"] = 22
        item.summary = f"{room}实测室温22℃，当前无需降温"
        return item


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


def test_light_prefers_live_household_illuminance(monkeypatch):
    decision = run_plan(
        build_agent(monkeypatch), AgentRequest(transcript="打开书房灯", user_id="1")
    )

    assert decision.status == DecisionStatus.EXECUTE
    assert decision.action is not None
    assert decision.action.parameters["brightness_percent"] == 80
    assert decision.action.command == "打开书房灯并调到80%亮度"
    assert any(item.kind == "household_state" for item in decision.evidence)
    assert all(item.kind != "environment" for item in decision.evidence)


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


def test_natural_short_heat_expression_is_recognized(monkeypatch):
    agent = build_agent(monkeypatch)
    decision = run_plan(agent, AgentRequest(transcript="我热了", user_id="1"))

    assert agent.might_be_home_request("我热了")
    assert decision.status == DecisionStatus.EXECUTE
    assert decision.action is not None
    assert decision.action.command == "打开客厅空调并设置为25度"


def test_stuffy_room_proposes_fresh_air_with_confirmation(monkeypatch):
    decision = run_plan(
        build_agent(monkeypatch), AgentRequest(transcript="屋里很闷", user_id="1")
    )

    assert decision.status == DecisionStatus.EXECUTE
    assert decision.action is not None
    assert decision.action.device == "新风"
    assert decision.action.command == "打开客厅新风"
    assert decision.action.requires_confirmation is True


def test_bright_room_recommends_lower_light_level(monkeypatch):
    decision = run_plan(
        build_agent(monkeypatch), AgentRequest(transcript="灯太亮了", user_id="1")
    )

    assert decision.status == DecisionStatus.EXECUTE
    assert decision.action is not None
    assert decision.action.parameters["brightness_percent"] == 30
    assert decision.action.command == "打开客厅灯并调到30%亮度"


class FixedChoice:
    def __init__(self, index: int) -> None:
        self.index = index

    def choice(self, values):
        return values[self.index % len(values)]


def test_fatigue_proposes_a_bounded_contextual_action_with_confirmation(monkeypatch):
    agent = build_agent(monkeypatch)
    agent._rng = FixedChoice(0)
    decision = run_plan(agent, AgentRequest(transcript="我累了", user_id="1"))

    assert agent.might_be_home_request("我累了")
    assert agent.might_be_wellbeing_request("我累了")
    assert not agent.might_be_advice_only_request("我累了")
    assert decision.status == DecisionStatus.EXECUTE
    assert decision.action is not None
    assert decision.action.device in {"空调", "风扇", "音乐播放器"}
    assert decision.action.device == "风扇"
    assert decision.action.action == "open"
    assert decision.action.command == "打开客厅风扇"
    assert decision.action.requires_confirmation is True
    assert "五到十分钟" in decision.user_message
    assert "建议打开风扇" in decision.user_message
    assert any(item.kind == "household_state" for item in decision.evidence)
    assert any(item.kind == "weather" for item in decision.evidence)


def test_relaxation_fallback_varies_between_equally_safe_devices(monkeypatch):
    fan_agent = build_agent(monkeypatch)
    fan_agent._rng = FixedChoice(0)
    music_agent = build_agent(monkeypatch)
    music_agent._rng = FixedChoice(-1)

    fan = run_plan(fan_agent, AgentRequest(transcript="我累了", user_id="1"))
    music = run_plan(music_agent, AgentRequest(transcript="我累了", user_id="1"))

    assert fan.action is not None
    assert music.action is not None
    assert fan.action.device == "风扇"
    assert music.action.device == "音乐播放器"
    assert fan.action.device != music.action.device


def test_relaxation_can_recommend_air_conditioner_strong_mode(monkeypatch):
    agent = build_agent(monkeypatch)
    agent._rng = FixedChoice(1)

    decision = run_plan(agent, AgentRequest(transcript="我累了", user_id="1"))

    assert decision.action is not None
    assert decision.action.device == "空调"
    assert decision.action.action == "set"
    assert decision.action.parameters == {"temperature_c": 25, "mode": "强力"}
    assert decision.action.command == "打开客厅空调并设置为25度强力模式"
    assert "强力模式" in decision.user_message


def test_relaxation_does_not_randomly_cool_an_already_cool_room(monkeypatch):
    agent = build_agent(monkeypatch)
    agent._data_tools = CoolDataTools()
    agent._rng = FixedChoice(1)

    decision = run_plan(agent, AgentRequest(transcript="我累了", user_id="1"))

    assert decision.action is not None
    assert decision.action.device == "音乐播放器"
    assert decision.action.command == "播放一首舒缓的轻音乐"


def test_direct_relaxing_music_request_uses_provider_channel(monkeypatch):
    agent = build_agent(monkeypatch)
    decision = run_plan(
        agent, AgentRequest(transcript="播放一首舒缓的轻音乐", user_id="1")
    )

    assert agent.might_be_home_request("播放一首舒缓的轻音乐")
    assert decision.status == DecisionStatus.EXECUTE
    assert decision.action is not None
    assert decision.action.device == "音乐播放器"
    assert decision.action.action == "play"
    assert decision.action.command == "播放一首舒缓的轻音乐"


def test_thirst_remains_advice_only_without_device_provider(monkeypatch):
    agent = build_agent(monkeypatch)
    decision = run_plan(agent, AgentRequest(transcript="我渴了", user_id="1"))

    assert agent.might_be_advice_only_request("我渴了")
    assert decision.status == DecisionStatus.ADVISE
    assert decision.action is None


def test_health_alert_only_triggers_emergency_notice(monkeypatch):
    decision = run_plan(
        build_agent(monkeypatch),
        AgentRequest(transcript="我胸痛而且呼吸困难", user_id="1"),
    )

    assert decision.status == DecisionStatus.ADVISE
    assert decision.action is None
    assert "120" in decision.user_message


def test_health_handler_priority_wins_over_device_action(monkeypatch):
    decision = run_plan(
        build_agent(monkeypatch),
        AgentRequest(transcript="我胸痛，顺便打开空调", user_id="1"),
    )

    assert decision.status == DecisionStatus.ADVISE
    assert decision.action is None
    assert "120" in decision.user_message


class MovieNightIntentHandler:
    name = "movie_night"
    priority = 850

    def matches(self, context: IntentContext) -> bool:
        return "观影模式" in context.text

    def accepts_as_entrypoint(self, context: IntentContext) -> bool:
        return self.matches(context)

    def analyze(self, context: IntentContext):
        return {
            "route": "clarify",
            "device": "投影仪",
            "room": "客厅",
            "risk_level": RiskLevel.L1,
        }


def test_registered_intent_handler_is_discovered_and_routed(monkeypatch):
    agent = build_agent(monkeypatch)
    agent.register_intent_handler(MovieNightIntentHandler())

    assert agent.might_be_home_request("进入观影模式")
    decision = run_plan(
        agent,
        AgentRequest(transcript="进入观影模式", user_id="1"),
    )

    assert decision.status == DecisionStatus.CLARIFY
    assert "客厅投影仪" in decision.user_message
    catalog = agent.intent_handler_catalog()
    names = [item["name"] for item in catalog]
    assert names[:3] == ["health_alert", "unsafe_device", "movie_night"]
    assert names[-1] == "not_applicable"


def test_negated_feeling_does_not_enter_agent(monkeypatch):
    assert not build_agent(monkeypatch).might_be_home_request("我现在不累了")


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
