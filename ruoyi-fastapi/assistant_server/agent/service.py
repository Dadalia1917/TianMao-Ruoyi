from __future__ import annotations

import json
import logging
import random
import re
import uuid
from datetime import datetime
from typing import Any, Literal, TypedDict
from zoneinfo import ZoneInfo

import httpx
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from ..config import Settings
from .prompts import (
    HOUSEHOLD_AGENT_PROMPT,
    WELLBEING_ADVICE_PROMPT,
    build_user_prompt,
    build_wellbeing_prompt,
)
from .schemas import (
    ActionLevel,
    AgentDecision,
    AgentRequest,
    DecisionStatus,
    DeviceAction,
    Evidence,
    HouseholdStateSnapshot,
    HouseholdStateUpdate,
    ModelPlan,
    RiskLevel,
    WellbeingAdvice,
)
from .tools import HouseholdDataTools
from .state import HouseholdStateStore

logger = logging.getLogger(__name__)


_DEVICE_ALIASES: tuple[tuple[str, str], ...] = (
    ("音乐播放器", "音乐播放器"),
    ("轻音乐", "音乐播放器"),
    ("音乐", "音乐播放器"),
    ("歌曲", "音乐播放器"),
    ("空气净化器", "空气净化器"),
    ("扫地机器人", "扫地机器人"),
    ("智能插座", "智能插座"),
    ("普通插座", "普通插座"),
    ("投影仪", "投影仪"),
    ("投影机", "投影仪"),
    ("加湿器", "加湿器"),
    ("除湿机", "除湿机"),
    ("净化器", "空气净化器"),
    ("扫地机", "扫地机器人"),
    ("新风", "新风"),
    ("空调", "空调"),
    ("窗帘", "窗帘"),
    ("纱帘", "窗帘"),
    ("百叶帘", "窗帘"),
    ("电视", "电视"),
    ("风扇", "风扇"),
    ("投影", "投影仪"),
    ("照明", "灯"),
    ("灯", "灯"),
    ("插座", "智能插座"),
)
_ROOMS = (
    "主卧", "次卧", "儿童房", "老人房", "客厅", "卧室", "书房", "厨房",
    "餐厅", "卫生间", "浴室", "阳台", "玄关", "全屋",
)
_UNSAFE = (
    "门锁", "开锁", "燃气", "燃气灶", "灶具", "电磁炉", "烤箱", "微波炉",
    "热水器", "车库门", "监控", "摄像头", "撤防", "报警器", "电热毯", "取暖器",
)
_NEGATIONS = ("不要", "别", "不用", "取消", "不需要")
_DISCUSSION = (
    "怎么", "如何", "为什么", "方法", "教程", "原理", "区别", "开了吗", "关了吗",
    "开着吗", "关着吗", "亮着吗", "有没有开", "有没有关", "设备状态",
    "我刚才说", "比如", "例如", "能不能控制", "可不可以控制",
)
_ACTION_WORDS = (
    "播放", "来一首", "放一首", "听",
    "打开", "开启", "启动", "关闭", "关掉", "停止", "调到", "调成", "设为", "设置为",
    "升高", "降低", "调高", "调低", "调亮", "调暗", "调大", "调小", "提高", "减小",
    "切换", "拉开", "拉上", "合上", "清扫", "扫地", "回充", "开", "关",
)
_COMFORT_PATTERNS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "hot",
        ("有点热", "好热", "太热", "很热", "闷热", "热死了", "我热了", "热了", "感觉热", "屋里热"),
        "空调",
    ),
    (
        "cold",
        ("有点冷", "好冷", "太冷", "很冷", "冻死了", "我冷了", "冷了", "感觉冷", "屋里冷"),
        "空调",
    ),
    ("dark", ("有点暗", "太暗", "好暗", "看不清", "屋里黑", "房间黑", "光线太暗"), "灯"),
    ("bright", ("太亮", "有点刺眼", "很刺眼", "光线刺眼", "灯太亮"), "灯"),
    ("humid", ("有点潮", "太潮", "好潮", "湿气重", "太湿了"), "除湿机"),
    ("dry", ("有点干", "太干", "好干", "空气干燥"), "加湿器"),
    ("stuffy", ("有点闷", "好闷", "太闷", "空气有点闷", "屋里很闷", "房间很闷", "不通风", "想透透气"), "新风"),
    ("air_quality", ("空气不好", "空气有味道", "有异味", "灰尘很大", "空气不舒服"), "空气净化器"),
)

_WELLBEING_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("fatigue", ("我累了", "有点累", "好累", "太累", "很疲惫", "有点疲惫", "精疲力尽")),
    ("sleepy", ("我困了", "有点困", "好困", "太困", "困死了", "想睡觉", "犯困")),
    ("sleep_problem", ("睡不着", "失眠了", "一直没睡着", "难以入睡")),
    ("stress", ("压力很大", "压力好大", "有点焦虑", "很焦虑", "心里很烦", "好烦", "太烦了", "很烦躁", "想放松", "我想放松一下")),
    ("thirst", ("我渴了", "有点渴", "好渴", "口渴")),
    ("hunger", ("我饿了", "有点饿", "好饿", "肚子饿")),
    ("headache", ("有点头疼", "有点头痛", "头有点晕", "轻微头晕")),
    ("noise", ("太吵了", "有点吵", "噪音好大", "声音太吵")),
)

_RELAXATION_SCENARIOS = {"fatigue", "stress"}
_RELAXATION_DEVICES = ("空调", "风扇", "音乐播放器")

_HEALTH_ALERTS = (
    "胸痛", "胸口剧痛", "呼吸困难", "喘不上气", "无法呼吸", "昏倒", "昏厥",
    "意识不清", "严重过敏", "嘴唇发紫", "突然说不清话", "一侧无力",
)

_NEGATED_FEELINGS = (
    "不热", "不冷", "不累", "不困", "不渴", "不饿", "不焦虑", "不烦",
    "没有压力", "没那么累", "没那么困", "没事",
)


class AgentState(TypedDict, total=False):
    request: AgentRequest
    request_id: str
    execution_id: str
    device: str
    room: str
    action: str
    risk_level: RiskLevel
    needs_context: bool
    route: Literal[
        "not_applicable",
        "blocked",
        "clarify",
        "direct",
        "contextual",
        "wellbeing",
        "health_notice",
    ]
    evidence: list[Evidence]
    model_plan: ModelPlan
    used_function_calling: bool
    comfort_intent: str
    wellbeing_scenario: str
    allowed_devices: tuple[str, ...]
    decision: AgentDecision


class HouseholdAgentService:
    """Single orchestrator with bounded tools and deterministic safety gates."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enabled = settings.agent_enabled
        self.ready = False
        self._client: httpx.AsyncClient | None = None
        self._data_tools: HouseholdDataTools | None = None
        self._rng = random.SystemRandom()
        self._state_store = HouseholdStateStore(
            ttl_seconds=settings.agent_household_state_ttl_seconds,
            redis_host=settings.agent_state_redis_host,
            redis_port=settings.agent_state_redis_port,
            redis_password=settings.agent_state_redis_password,
            redis_db=settings.agent_state_redis_db,
        )
        graph = StateGraph(AgentState)
        graph.add_node("analyze", self._analyze)
        graph.add_node("blocked", self._blocked)
        graph.add_node("clarify", self._clarify)
        graph.add_node("not_applicable", self._not_applicable)
        graph.add_node("direct_plan", self._direct_plan)
        graph.add_node("context_plan", self._context_plan)
        graph.add_node("wellbeing", self._wellbeing_advice)
        graph.add_node("health_notice", self._health_notice)
        graph.add_node("validate", self._validate)
        graph.add_edge(START, "analyze")
        graph.add_conditional_edges(
            "analyze",
            lambda state: state["route"],
            {
                "blocked": "blocked",
                "clarify": "clarify",
                "not_applicable": "not_applicable",
                "direct": "direct_plan",
                "contextual": "context_plan",
                "wellbeing": "wellbeing",
                "health_notice": "health_notice",
            },
        )
        graph.add_edge("blocked", END)
        graph.add_edge("clarify", END)
        graph.add_edge("not_applicable", END)
        graph.add_edge("direct_plan", "validate")
        graph.add_edge("context_plan", "validate")
        graph.add_edge("wellbeing", END)
        graph.add_edge("health_notice", END)
        graph.add_edge("validate", END)
        self._graph = graph.compile()

    async def start(self) -> None:
        if not self.enabled:
            logger.info("household agent disabled")
            return
        await self._state_store.start()
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.settings.dashscope_api_key}"},
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
        self._data_tools = HouseholdDataTools(
            self._client,
            latitude=self.settings.agent_latitude,
            longitude=self.settings.agent_longitude,
            timezone=self.settings.agent_timezone,
            location_name=self.settings.agent_location_name,
            weather_enabled=self.settings.agent_weather_enabled,
            simulated_environment_enabled=(
                self.settings.agent_simulated_environment_enabled
            ),
            state_store=self._state_store,
        )
        self.ready = bool(self.settings.dashscope_api_key)
        logger.info(
            "household agent ready: model=%s location=%s weather=%s simulated_environment=%s state_backend=%s",
            self.settings.agent_model,
            self.settings.agent_location_name,
            self.settings.agent_weather_enabled,
            self.settings.agent_simulated_environment_enabled,
            self._state_store.backend,
        )

    async def close(self) -> None:
        self.ready = False
        if self._client:
            await self._client.aclose()
        await self._state_store.close()
        self._client = None
        self._data_tools = None

    def might_be_home_request(self, transcript: str) -> bool:
        text = "".join(str(transcript or "").split())
        if any(marker in text for marker in _HEALTH_ALERTS):
            return True
        if self._wellbeing_scenario(text):
            return not any(marker in text for marker in _NEGATED_FEELINGS)
        if self._comfort_intent(text):
            if any(marker in text for marker in _NEGATIONS + _NEGATED_FEELINGS):
                return False
            return not any(marker in text for marker in _DISCUSSION)
        has_device = any(alias in text for alias, _ in _DEVICE_ALIASES) or any(
            marker in text for marker in _UNSAFE
        )
        has_action = any(marker in text for marker in _ACTION_WORDS)
        if not text or not has_device or not has_action:
            return False
        if any(marker in text for marker in _NEGATIONS):
            return False
        return not any(marker in text for marker in _DISCUSSION)

    def might_be_wellbeing_request(self, transcript: str) -> bool:
        """Return true for recognized human-state scenarios, including urgent notices."""
        text = "".join(str(transcript or "").split())
        if any(marker in text for marker in _HEALTH_ALERTS):
            return True
        return bool(self._wellbeing_scenario(text)) and not any(
            marker in text for marker in _NEGATED_FEELINGS
        )

    def might_be_advice_only_request(self, transcript: str) -> bool:
        """Return true when the Agent can answer without a working device provider."""
        text = "".join(str(transcript or "").split())
        if any(marker in text for marker in _HEALTH_ALERTS):
            return True
        scenario = self._wellbeing_scenario(text)
        return bool(scenario and scenario not in _RELAXATION_SCENARIOS) and not any(
            marker in text for marker in _NEGATED_FEELINGS
        )

    async def update_household_state(
        self, user_id: str, room: str, update: HouseholdStateUpdate
    ) -> HouseholdStateSnapshot:
        return await self._state_store.update(user_id, room, update)

    async def get_household_state(
        self, user_id: str, room: str
    ) -> HouseholdStateSnapshot | None:
        return await self._state_store.get(user_id, room)

    async def clear_household_state(self, user_id: str, room: str | None = None) -> int:
        return await self._state_store.clear(user_id, room)

    async def plan(self, request: AgentRequest) -> AgentDecision:
        result = await self._graph.ainvoke(
            {
                "request": request,
                "request_id": uuid.uuid4().hex,
                "execution_id": uuid.uuid4().hex,
                "evidence": [],
                "used_function_calling": False,
            }
        )
        return result["decision"]

    def _now(self) -> datetime:
        try:
            return datetime.now(ZoneInfo(self.settings.agent_timezone))
        except Exception:
            return datetime.now().astimezone()

    def _base_decision(
        self,
        state: AgentState,
        *,
        status: DecisionStatus,
        user_message: str,
        rationale: str = "",
        action: DeviceAction | None = None,
    ) -> AgentDecision:
        return AgentDecision(
            request_id=state["request_id"],
            execution_id=state["execution_id"],
            status=status,
            user_message=user_message,
            rationale=rationale,
            decision_basis=[
                f"{item.kind}：{item.summary}" for item in state.get("evidence", [])
            ][:12],
            action=action,
            evidence=state.get("evidence", []),
            used_function_calling=state.get("used_function_calling", False),
            created_at=self._now(),
        )

    def _analyze(self, state: AgentState) -> dict[str, Any]:
        text = "".join(state["request"].transcript.split())
        if any(marker in text for marker in _HEALTH_ALERTS):
            return {
                "route": "health_notice",
                "risk_level": RiskLevel.L4,
                "wellbeing_scenario": "health_alert",
            }
        if any(marker in text for marker in _UNSAFE):
            return {"route": "blocked", "risk_level": RiskLevel.L4}
        wellbeing_scenario = self._wellbeing_scenario(text)
        if wellbeing_scenario in _RELAXATION_SCENARIOS:
            return {
                "route": "contextual",
                "device": "",
                "room": next(
                    (name for name in _ROOMS if name in text),
                    self.settings.agent_default_room,
                ),
                "action": "recommend",
                "risk_level": RiskLevel.L2,
                "needs_context": True,
                "comfort_intent": "relax",
                "wellbeing_scenario": wellbeing_scenario,
                "allowed_devices": _RELAXATION_DEVICES,
            }
        comfort_intent = self._comfort_intent(text)
        if comfort_intent:
            device = next(
                device
                for name, _markers, device in _COMFORT_PATTERNS
                if name == comfort_intent
            )
            room = next(
                (name for name in _ROOMS if name in text),
                self.settings.agent_default_room,
            )
            return {
                "route": "contextual",
                "device": device,
                "room": room,
                "action": "set" if device in {"空调", "灯"} else "open",
                "risk_level": RiskLevel.L2 if device == "空调" else RiskLevel.L1,
                "needs_context": True,
                "comfort_intent": comfort_intent,
            }
        if wellbeing_scenario:
            return {
                "route": "wellbeing",
                "risk_level": RiskLevel.L0,
                "needs_context": True,
                "wellbeing_scenario": wellbeing_scenario,
                "room": next(
                    (name for name in _ROOMS if name in text),
                    self.settings.agent_default_room,
                ),
            }
        device = next((canonical for alias, canonical in _DEVICE_ALIASES if alias in text), "")
        if not device or not self.might_be_home_request(text):
            return {"route": "not_applicable", "device": device}
        room = next((name for name in _ROOMS if name in text), "")
        if "开关" in text and not any(word in text for word in ("打开", "开启", "关闭", "关掉")):
            return {"route": "clarify", "device": device, "room": room}
        if any(word in text for word in ("关闭", "关掉", "停止")):
            action = "close"
        elif any(word in text for word in ("播放", "来一首", "放一首", "听")):
            action = "play"
        elif "回充" in text:
            action = "dock"
        elif any(word in text for word in ("清扫", "扫地")):
            action = "clean"
        elif any(word in text for word in ("调到", "调成", "设为", "设置为", "调高", "调低", "调亮", "调暗")):
            action = "set"
        elif any(word in text for word in ("打开", "开启", "启动", "开")):
            action = "open"
        else:
            action = "set"
        needs_context = True
        return {
            "route": "contextual",
            "device": device,
            "room": room,
            "action": action,
            "risk_level": RiskLevel.L2 if device == "空调" else RiskLevel.L1,
            "needs_context": needs_context,
        }

    @staticmethod
    def _comfort_intent(text: str) -> str:
        for name, markers, _device in _COMFORT_PATTERNS:
            if any(marker in text for marker in markers):
                return name
        return ""

    @staticmethod
    def _wellbeing_scenario(text: str) -> str:
        for name, markers in _WELLBEING_PATTERNS:
            if any(marker in text for marker in markers):
                return name
        return ""

    def _blocked(self, state: AgentState) -> dict[str, Any]:
        return {
            "decision": self._base_decision(
                state,
                status=DecisionStatus.BLOCKED,
                user_message="这项操作涉及较高安全风险，当前助手不会代为执行。",
                rationale="安全策略禁止自动控制门锁、燃气、加热烹饪或安防设备。",
            )
        }

    def _clarify(self, state: AgentState) -> dict[str, Any]:
        return {
            "decision": self._base_decision(
                state,
                status=DecisionStatus.CLARIFY,
                user_message=f"您希望把{state.get('room', '')}{state.get('device', '设备')}打开还是关闭？",
                rationale="用户尚未给出明确的最终状态。",
            )
        }

    def _not_applicable(self, state: AgentState) -> dict[str, Any]:
        return {
            "decision": self._base_decision(
                state,
                status=DecisionStatus.NOT_APPLICABLE,
                user_message="这不是一条可执行的家居控制指令。",
            )
        }

    def _health_notice(self, state: AgentState) -> dict[str, Any]:
        return {
            "decision": self._base_decision(
                state,
                status=DecisionStatus.ADVISE,
                user_message=(
                    "这可能是需要立即处理的健康风险。请马上停止当前活动，联系身边的人并拨打120；"
                    "如果环境存在危险，先在确保自身安全的前提下离开危险源。"
                ),
                rationale="检测到胸痛、呼吸困难、意识异常等紧急风险表达，安全提醒优先且不触发家电。",
            )
        }

    def _direct_plan(self, state: AgentState) -> dict[str, Any]:
        transcript = state["request"].transcript.strip()
        command = self._normalize_command(transcript)
        plan = ModelPlan(
            command=command,
            device=state["device"],
            room=state.get("room", ""),
            action=state["action"],
            user_message="好的，正在为您处理。",
            rationale="用户给出了明确的低风险设备控制要求。",
            parameters=self._extract_parameters(transcript),
        )
        return {"model_plan": plan}

    async def _context_plan(self, state: AgentState) -> dict[str, Any]:
        if not self._data_tools:
            return self._fallback_context_plan(state, [])
        if not self.ready or not self._client:
            evidence = await self._ensure_context_evidence(state, [])
            return self._fallback_context_plan(state, evidence)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": HOUSEHOLD_AGENT_PROMPT},
            {
                "role": "user",
                "content": build_user_prompt(
                    state["request"].transcript,
                    state["request"].location_name or self.settings.agent_location_name,
                    state["request"].memory_context,
                ),
            },
        ]
        evidence: list[Evidence] = []
        used_function_calling = False
        try:
            for _ in range(self.settings.agent_max_tool_rounds):
                payload = {
                    "model": self.settings.agent_model,
                    "messages": messages,
                    "tools": self._tool_definitions(),
                    "tool_choice": "auto",
                    "enable_thinking": False,
                    "temperature": (
                        0.35
                        if state.get("wellbeing_scenario") in _RELAXATION_SCENARIOS
                        else 0.1
                    ),
                    "max_tokens": 900,
                }
                response = await self._client.post(
                    self.settings.agent_api_url,
                    json=payload,
                    timeout=self.settings.agent_timeout_seconds,
                )
                response.raise_for_status()
                message = response.json()["choices"][0]["message"]
                messages.append(message)
                tool_calls = message.get("tool_calls") or []
                if not tool_calls:
                    break
                used_function_calling = True
                for tool_call in tool_calls:
                    function = tool_call.get("function") or {}
                    name = function.get("name", "")
                    arguments = self._json_object(function.get("arguments"))
                    logger.info(
                        "agent tool invoke: request=%s execution=%s user=%s tool=%s",
                        state["request_id"],
                        state["execution_id"],
                        state["request"].user_id,
                        name,
                    )
                    if name == "get_weather":
                        item = await self._data_tools.get_weather()
                        evidence = self._replace_evidence(evidence, item)
                        output: Any = item.model_dump(mode="json")
                    elif name == "get_environment":
                        item = await self._data_tools.get_environment()
                        evidence = self._replace_evidence(evidence, item)
                        output = item.model_dump(mode="json")
                    elif name == "get_household_state":
                        item = await self._data_tools.get_household_state(
                            user_id=state["request"].user_id,
                            room=state.get("room") or self.settings.agent_default_room,
                            memory_context=state["request"].memory_context,
                        )
                        evidence = self._replace_evidence(evidence, item)
                        output = item.model_dump(mode="json")
                    elif name == "submit_home_plan":
                        missing = self._missing_required_evidence(state, evidence)
                        if missing:
                            output = {
                                "error": "missing_required_evidence",
                                "required": missing,
                                "message": "请先调用缺失的家庭状态工具，再提交计划。",
                            }
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.get("id", ""),
                                    "name": name,
                                    "content": json.dumps(output, ensure_ascii=False),
                                }
                            )
                            continue
                        plan = ModelPlan.model_validate(arguments)
                        evidence = self._prune_redundant_environment(evidence)
                        return {
                            "model_plan": plan,
                            "evidence": evidence,
                            "used_function_calling": True,
                        }
                    else:
                        output = {"error": "unsupported_tool"}
                    logger.info(
                        "agent tool result: request=%s execution=%s tool=%s accepted=%s",
                        state["request_id"],
                        state["execution_id"],
                        name,
                        not (isinstance(output, dict) and output.get("error")),
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.get("id", ""),
                            "name": name,
                            "content": json.dumps(output, ensure_ascii=False),
                        }
                    )
        except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError):
            logger.exception("household agent model planning failed; using policy fallback")
        evidence = await self._ensure_context_evidence(state, evidence)
        fallback = self._fallback_context_plan(state, evidence)
        fallback["used_function_calling"] = used_function_calling
        return fallback

    async def _wellbeing_advice(self, state: AgentState) -> dict[str, Any]:
        evidence: list[Evidence] = []
        if self._data_tools:
            evidence = self._replace_evidence(
                evidence,
                await self._data_tools.get_household_state(
                    user_id=state["request"].user_id,
                    room=state.get("room") or self.settings.agent_default_room,
                    memory_context=state["request"].memory_context,
                ),
            )
        scenario = state.get("wellbeing_scenario", "fatigue")
        fallback_message, fallback_rationale = self._fallback_wellbeing_advice(
            scenario, evidence
        )
        advice = WellbeingAdvice(
            user_message=fallback_message,
            rationale=fallback_rationale,
        )
        used_function_calling = False
        if self.ready and self._client:
            try:
                payload = {
                    "model": self.settings.agent_model,
                    "messages": [
                        {"role": "system", "content": WELLBEING_ADVICE_PROMPT},
                        {
                            "role": "user",
                            "content": build_wellbeing_prompt(
                                state["request"].transcript,
                                scenario,
                                state["request"].location_name
                                or self.settings.agent_location_name,
                                [item.summary for item in evidence],
                                state["request"].memory_context,
                            ),
                        },
                    ],
                    "tools": [self._wellbeing_tool_definition()],
                    "tool_choice": {
                        "type": "function",
                        "function": {"name": "submit_wellbeing_advice"},
                    },
                    "enable_thinking": False,
                    "temperature": 0.2,
                    "max_tokens": 500,
                }
                response = await self._client.post(
                    self.settings.agent_api_url,
                    json=payload,
                    timeout=self.settings.agent_timeout_seconds,
                )
                response.raise_for_status()
                message = response.json()["choices"][0]["message"]
                tool_call = next(
                    (
                        item
                        for item in (message.get("tool_calls") or [])
                        if (item.get("function") or {}).get("name")
                        == "submit_wellbeing_advice"
                    ),
                    None,
                )
                if tool_call:
                    model_advice = WellbeingAdvice.model_validate(
                        self._json_object((tool_call.get("function") or {}).get("arguments"))
                    )
                    used_function_calling = True
                    if any(
                        alias in model_advice.user_message
                        for alias, _canonical in _DEVICE_ALIASES
                    ) or any(marker in model_advice.user_message for marker in _UNSAFE):
                        logger.warning(
                            "wellbeing advice mentioned a controlled device; using safe fallback: scenario=%s",
                            scenario,
                        )
                    else:
                        advice = model_advice
            except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError):
                logger.exception(
                    "wellbeing advice model failed; using deterministic fallback: scenario=%s",
                    scenario,
                )
        state_with_evidence = dict(state)
        state_with_evidence["evidence"] = evidence
        state_with_evidence["used_function_calling"] = used_function_calling
        return {
            "evidence": evidence,
            "used_function_calling": used_function_calling,
            "decision": self._base_decision(
                state_with_evidence,
                status=DecisionStatus.ADVISE,
                user_message=advice.user_message,
                rationale=advice.rationale,
            ),
        }

    def _fallback_wellbeing_advice(
        self, scenario: str, evidence: list[Evidence]
    ) -> tuple[str, str]:
        suggestions = {
            "fatigue": "建议先坐下休息五到十分钟，少量补水并暂时停止连续用眼；如果休息后仍明显乏力或持续加重，请联系家人并考虑就医。",
            "sleepy": "如果环境安全，建议先停止驾车、登高或操作设备，再安排二十分钟左右的小睡；醒来后补水并活动一下。",
            "sleep_problem": "建议先把灯光和屏幕调暗，进行几分钟缓慢呼吸；二十分钟仍无睡意时可暂时离床做安静活动，困倦后再尝试入睡。",
            "stress": "建议先做两分钟缓慢呼吸，暂时降低声音和屏幕刺激，再只选最紧急的一件事拆成一个小步骤处理。",
            "thirst": "建议少量多次补水，先避免大量含糖或含咖啡因饮料；如果异常口渴持续并伴随明显不适，请考虑就医。",
            "hunger": "建议先选择一份清淡、适量的食物并慢慢进食；临睡前避免一次吃得过多。",
            "headache": "建议先停止盯屏，坐下休息并少量补水；如果突然剧烈、持续加重，或伴随说话不清、一侧无力等情况，请立即联系120。",
            "noise": "建议先离开持续噪声源或关闭不必要的声源，给自己几分钟安静时间；不要长时间用过高耳机音量遮盖噪声。",
        }
        context = evidence[0].summary if evidence else "当前没有可靠的家庭传感器数据"
        suggestion = suggestions.get(
            scenario,
            "建议先短暂休息、补水并观察感受变化；如果持续或明显加重，请联系家人或专业医护人员。",
        )
        return f"{context}。{suggestion}", f"结合{context}给出非医疗性的生活建议。"

    def _validate(self, state: AgentState) -> dict[str, Any]:
        plan = state["model_plan"]
        planned_device = next(
            (
                canonical
                for alias, canonical in _DEVICE_ALIASES
                if alias in plan.device or alias in plan.command
            ),
            "",
        )
        is_relaxation = state.get("wellbeing_scenario") in _RELAXATION_SCENARIOS
        effective_state: AgentState = state
        device = state.get("device", "")
        if is_relaxation:
            previous_device = self._previous_relaxation_device(
                state["request"].transcript
            )
            if (
                previous_device and planned_device == previous_device
            ) or not self._relaxation_device_is_contextually_allowed(
                planned_device, state.get("evidence", [])
            ):
                plan = self._fallback_relaxation_plan(
                    state, state.get("evidence", [])
                )["model_plan"]
                planned_device = next(
                    (
                        canonical
                        for alias, canonical in _DEVICE_ALIASES
                        if alias in plan.device or alias in plan.command
                    ),
                    "",
                )
            allowed_devices = set(state.get("allowed_devices") or _RELAXATION_DEVICES)
            if planned_device not in allowed_devices:
                return {
                    "decision": self._base_decision(
                        state,
                        status=DecisionStatus.BLOCKED,
                        user_message="计划未通过安全校验，未提交设备操作。",
                        rationale="放松场景的建议超出了空调、风扇和音乐播放器的低风险白名单。",
                    )
                }
            device = planned_device
            effective_state = dict(state)
            effective_state["device"] = device
            effective_state["room"] = "" if device == "音乐播放器" else (
                state.get("room") or self.settings.agent_default_room
            )
            effective_state["action"] = {
                "空调": "set",
                "风扇": "open",
                "音乐播放器": "play",
            }[device]
            effective_state["risk_level"] = (
                RiskLevel.L2 if device == "空调" else RiskLevel.L1
            )
        if any(marker in plan.command for marker in _UNSAFE) or (
            not is_relaxation and planned_device and planned_device != device
        ):
            return {
                "decision": self._base_decision(
                    state,
                    status=DecisionStatus.BLOCKED,
                    user_message="计划未通过安全校验，未提交设备操作。",
                    rationale="模型计划超出了已识别设备或安全范围。",
                )
            }
        parameters = self._sanitize_parameters(device, plan.parameters)
        # The model may recommend a parameter only when the user left it open.
        # Explicit safe values from the transcript always win over model output
        # and long-term preference memory.
        parameters.update(
            self._sanitize_parameters(
                device,
                self._extract_parameters(state["request"].transcript),
            )
        )
        command = self._enforce_recommended_command(
            effective_state, plan.command, parameters
        )
        action = DeviceAction(
            command=command,
            device=device,
            room=effective_state.get("room", ""),
            action=effective_state["action"],
            parameters=parameters,
            action_level=ActionLevel.A2 if device in {"空调", "灯"} else ActionLevel.A1,
            risk_level=effective_state.get("risk_level", RiskLevel.L1),
            requires_confirmation=True,
        )
        return {
            "decision": self._base_decision(
                state,
                status=DecisionStatus.EXECUTE,
                user_message=self._contextual_user_message(
                    effective_state, state.get("evidence", []), parameters
                ),
                rationale=plan.rationale,
                action=action,
            )
        }

    def _fallback_context_plan(
        self, state: AgentState, evidence: list[Evidence]
    ) -> dict[str, Any]:
        if state.get("wellbeing_scenario") in _RELAXATION_SCENARIOS:
            return self._fallback_relaxation_plan(state, evidence)
        transcript = state["request"].transcript
        params = self._extract_parameters(transcript)
        room_device = f"{state.get('room', '')}{state['device']}"
        rationale = "按用户明确要求执行。"
        if state["device"] == "空调" and "temperature_c" not in params:
            weather = next((item for item in evidence if item.kind == "weather"), None)
            household = next(
                (item for item in evidence if item.kind == "household_state"), None
            )
            outside = weather.data.get("temperature_c") if weather else None
            indoor = household.data.get("indoor_temperature_c") if household else None
            preferred = household.data.get("preferred_temperature_c") if household else None
            temperature = self._recommended_ac_temperature(
                outside,
                indoor=indoor,
                preferred=preferred,
                comfort_intent=state.get("comfort_intent", ""),
            )
            params["temperature_c"] = temperature
            rationale = self._air_conditioner_rationale(
                state, weather, household, temperature
            )
        if state["device"] == "灯" and "brightness_percent" not in params:
            household = next(
                (item for item in evidence if item.kind == "household_state"), None
            )
            environment = next((item for item in evidence if item.kind == "environment"), None)
            lux = (
                household.data.get("illuminance_lux")
                if household
                else environment.data.get("illuminance_lux") if environment else None
            )
            brightness = (
                30
                if state.get("comfort_intent") == "bright"
                else self._recommended_brightness(lux)
            )
            params["brightness_percent"] = brightness
            source = "实时室内照度" if household and not household.simulated else "模拟室内照度"
            rationale = f"根据{source}，建议亮度为{brightness}%。"
        command = self._command_from_parts(state, params, room_device)
        user_message = self._contextual_user_message(state, evidence, params)
        return {
            "model_plan": ModelPlan(
                command=command,
                device=state["device"],
                room=state.get("room", ""),
                action=state["action"],
                user_message=user_message,
                rationale=rationale,
                parameters=params,
            ),
            "evidence": evidence,
        }

    def _fallback_relaxation_plan(
        self, state: AgentState, evidence: list[Evidence]
    ) -> dict[str, Any]:
        household = next(
            (item for item in evidence if item.kind == "household_state"), None
        )
        weather = next((item for item in evidence if item.kind == "weather"), None)
        indoor = household.data.get("indoor_temperature_c") if household else None
        outside = weather.data.get("temperature_c") if weather else None
        preferred = household.data.get("preferred_temperature_c") if household else None

        if (
            isinstance(indoor, (int, float)) and indoor >= 29
        ) or (
            not isinstance(indoor, (int, float))
            and isinstance(outside, (int, float))
            and outside >= 33
        ):
            candidates = ("空调", "空调", "风扇", "音乐播放器")
        elif isinstance(indoor, (int, float)) and indoor >= 26:
            candidates = ("风扇", "空调", "风扇", "音乐播放器")
        elif isinstance(indoor, (int, float)) and indoor >= 23.5:
            candidates = ("音乐播放器", "风扇", "音乐播放器")
        else:
            candidates = ("音乐播放器",)
        previous_device = self._previous_relaxation_device(
            state["request"].transcript
        )
        if previous_device:
            alternatives = tuple(item for item in candidates if item != previous_device)
            if alternatives:
                candidates = alternatives
        device = self._rng.choice(candidates)
        effective_state: AgentState = dict(state)
        effective_state["device"] = device
        effective_state["room"] = "" if device == "音乐播放器" else (
            state.get("room") or self.settings.agent_default_room
        )
        effective_state["action"] = {
            "空调": "set",
            "风扇": "open",
            "音乐播放器": "play",
        }[device]

        params: dict[str, Any] = {}
        if device == "空调":
            params["temperature_c"] = self._recommended_ac_temperature(
                outside,
                indoor=indoor,
                preferred=preferred,
            )
            if isinstance(indoor, (int, float)) and indoor >= 28:
                params["mode"] = "强力"
            rationale = self._air_conditioner_rationale(
                effective_state,
                weather,
                household,
                params["temperature_c"],
            )
        elif device == "风扇":
            rationale = "结合当前室内温度，选择低风险的通风降温方案，并保留用户确认。"
        else:
            rationale = "当前更适合用舒缓音乐帮助放松，并同时建议短暂休息和补水。"
        room_device = f"{effective_state.get('room', '')}{device}"
        command = self._command_from_parts(effective_state, params, room_device)
        return {
            "model_plan": ModelPlan(
                command=command,
                device=device,
                room=effective_state.get("room", ""),
                action=effective_state["action"],
                user_message=self._contextual_user_message(
                    effective_state, evidence, params
                ),
                rationale=rationale,
                parameters=params,
            ),
            "evidence": evidence,
        }

    @staticmethod
    def _previous_relaxation_device(transcript: str) -> str:
        if "上一方案" not in transcript:
            return ""
        previous_text = transcript.split("上一方案", 1)[-1]
        return next(
            (
                canonical
                for alias, canonical in _DEVICE_ALIASES
                if alias in previous_text and canonical in _RELAXATION_DEVICES
            ),
            "",
        )

    @staticmethod
    def _relaxation_device_is_contextually_allowed(
        device: str, evidence: list[Evidence]
    ) -> bool:
        household = next(
            (item for item in evidence if item.kind == "household_state"), None
        )
        weather = next((item for item in evidence if item.kind == "weather"), None)
        indoor = household.data.get("indoor_temperature_c") if household else None
        outside = weather.data.get("temperature_c") if weather else None
        if device == "音乐播放器":
            return True
        if device == "空调":
            return (
                isinstance(indoor, (int, float)) and indoor >= 26
            ) or (
                not isinstance(indoor, (int, float))
                and isinstance(outside, (int, float))
                and outside >= 32
            )
        if device == "风扇":
            return (
                isinstance(indoor, (int, float)) and indoor >= 23.5
            ) or (
                not isinstance(indoor, (int, float))
                and isinstance(outside, (int, float))
                and outside >= 25
            )
        return False

    def _command_from_parts(
        self, state: AgentState, params: dict[str, Any], room_device: str
    ) -> str:
        action = state["action"]
        if state.get("device") == "音乐播放器" and action == "play":
            return "播放一首舒缓的轻音乐"
        if action == "close":
            return f"关闭{room_device}"
        if state["device"] == "空调" and "temperature_c" in params:
            mode = f"{params['mode']}模式" if params.get("mode") else ""
            return f"打开{room_device}并设置为{params['temperature_c']}度{mode}"
        if state["device"] == "灯" and "brightness_percent" in params:
            return f"打开{room_device}并调到{params['brightness_percent']}%亮度"
        if state.get("comfort_intent") and action == "open":
            return f"打开{room_device}"
        return self._normalize_command(state["request"].transcript)

    def _enforce_recommended_command(
        self, state: AgentState, command: str, params: dict[str, Any]
    ) -> str:
        room_device = f"{state.get('room', '')}{state['device']}"
        if state.get("device") == "音乐播放器" and state.get("action") == "play":
            return "播放一首舒缓的轻音乐"
        if state["action"] == "close":
            return f"关闭{room_device}"
        if state["device"] == "空调" and "temperature_c" in params:
            mode = f"{params['mode']}模式" if params.get("mode") else ""
            return f"打开{room_device}并设置为{params['temperature_c']}度{mode}"
        if state["device"] == "灯" and "brightness_percent" in params:
            return f"打开{room_device}并调到{params['brightness_percent']}%亮度"
        if state.get("comfort_intent") and state["action"] == "open":
            return f"打开{room_device}"
        return self._normalize_command(command)

    def _extract_parameters(self, transcript: str) -> dict[str, Any]:
        params: dict[str, Any] = {}
        temperature = re.search(r"(?<!\d)(1[6-9]|2\d|30)\s*(?:摄氏)?度", transcript)
        brightness = re.search(
            r"(?:(?<!\d)(100|[1-9]?\d)\s*%?\s*(?:亮度|亮)|"
            r"(?:亮度|亮)\D{0,6}(100|[1-9]?\d)\s*%?)",
            transcript,
        )
        if temperature:
            params["temperature_c"] = int(temperature.group(1))
        if brightness:
            params["brightness_percent"] = int(
                brightness.group(1) or brightness.group(2)
            )
        for mode in ("强力", "制冷", "制热", "除湿", "送风", "自动"):
            if mode in transcript:
                params["mode"] = mode
                break
        return params

    def _sanitize_parameters(self, device: str, parameters: dict[str, Any]) -> dict[str, Any]:
        result = dict(parameters or {})
        if "temperature_c" in result:
            try:
                result["temperature_c"] = max(16, min(30, int(result["temperature_c"])))
            except (TypeError, ValueError):
                result.pop("temperature_c", None)
        if "brightness_percent" in result:
            try:
                result["brightness_percent"] = max(
                    1, min(100, int(result["brightness_percent"]))
                )
            except (TypeError, ValueError):
                result.pop("brightness_percent", None)
        if device != "空调":
            result.pop("temperature_c", None)
            result.pop("mode", None)
        elif result.get("mode") not in {"强力", "制冷", "制热", "除湿", "送风", "自动"}:
            result.pop("mode", None)
        if device != "灯":
            result.pop("brightness_percent", None)
        return result

    def _recommended_ac_temperature(
        self,
        outside: Any,
        *,
        indoor: Any = None,
        preferred: Any = None,
        comfort_intent: str = "",
    ) -> int:
        if isinstance(preferred, (int, float)):
            base = int(preferred)
        elif comfort_intent == "hot":
            base = 25
        elif comfort_intent == "cold":
            base = 23
        elif not isinstance(outside, (int, float)):
            base = 26
        elif outside >= 34:
            base = 27
        elif outside >= 28:
            base = 26
        elif outside <= 8:
            base = 22
        elif outside <= 16:
            base = 23
        else:
            base = 25
        if comfort_intent == "hot" and isinstance(indoor, (int, float)):
            base = min(base, max(24, int(round(float(indoor) - 2))))
        if comfort_intent == "cold" and isinstance(indoor, (int, float)):
            base = max(base, min(25, int(round(float(indoor) + 2))))
        return max(16, min(30, base))

    def _recommended_brightness(self, lux: Any) -> int:
        if not isinstance(lux, (int, float)):
            return 60
        if lux < 80:
            return 80
        if lux < 250:
            return 65
        if lux < 500:
            return 45
        return 30

    def _air_conditioner_rationale(
        self,
        state: AgentState,
        weather: Evidence | None,
        household: Evidence | None,
        temperature: int,
    ) -> str:
        facts: list[str] = []
        if household:
            indoor = household.data.get("indoor_temperature_c")
            humidity = household.data.get("indoor_humidity_percent")
            period = household.data.get("time_period")
            preferred = household.data.get("preferred_temperature_c")
            if isinstance(indoor, (int, float)):
                facts.append(f"室内{float(indoor):.1f}℃")
            if isinstance(humidity, (int, float)):
                facts.append(f"湿度{float(humidity):.0f}%")
            if period:
                facts.append(str(period))
            if isinstance(preferred, (int, float)):
                facts.append(f"偏好{int(preferred)}℃")
        if weather:
            outside = weather.data.get("temperature_c")
            if isinstance(outside, (int, float)):
                facts.append(f"室外{float(outside):.1f}℃")
        return f"综合{'、'.join(facts) or '当前可用家庭状态'}，建议设置为{temperature}℃。"

    def _contextual_user_message(
        self,
        state: AgentState,
        evidence: list[Evidence],
        params: dict[str, Any],
    ) -> str:
        room = state.get("room") or self.settings.agent_default_room
        household = next(
            (item for item in evidence if item.kind == "household_state"), None
        )
        weather = next((item for item in evidence if item.kind == "weather"), None)
        if state.get("wellbeing_scenario") in _RELAXATION_SCENARIOS:
            feeling = "有些疲惫" if state.get("wellbeing_scenario") == "fatigue" else "需要放松"
            common = f"听起来你{feeling}，建议先休息五到十分钟、喝几口水。"
            indoor = household.data.get("indoor_temperature_c") if household else None
            outside = weather.data.get("temperature_c") if weather else None
            facts: list[str] = []
            if isinstance(indoor, (int, float)):
                facts.append(f"{room}约{float(indoor):.1f}℃")
            if isinstance(outside, (int, float)):
                facts.append(f"室外约{float(outside):.1f}℃")
            prefix = "、".join(facts)
            if state.get("device") == "空调":
                target = params.get("temperature_c", 26)
                mode = f"{params['mode']}模式" if params.get("mode") else ""
                proposal = f"建议把空调设为{target}℃{mode}"
            elif state.get("device") == "风扇":
                proposal = "建议打开风扇吹一会儿"
            else:
                proposal = "建议播放一首舒缓的轻音乐"
            context = f"结合{prefix}，" if prefix else ""
            return f"{common}{context}{proposal}。"
        if state.get("device") == "空调":
            target = params.get("temperature_c")
            indoor = household.data.get("indoor_temperature_c") if household else None
            humidity = household.data.get("indoor_humidity_percent") if household else None
            devices = household.data.get("device_states", {}) if household else {}
            ac_state = devices.get("空调", {}) if isinstance(devices, dict) else {}
            power = ac_state.get("power") if isinstance(ac_state, dict) else "unknown"
            parts: list[str] = []
            if isinstance(indoor, (int, float)):
                label = "当前" if household and not household.simulated else "估算"
                parts.append(f"{room}{label}{float(indoor):.1f}℃")
            if isinstance(humidity, (int, float)):
                parts.append(f"湿度{float(humidity):.0f}%")
            outside = weather.data.get("temperature_c") if weather else None
            if isinstance(outside, (int, float)):
                parts.append(f"室外{float(outside):.1f}℃")
            prefix = "，".join(parts)
            if state.get("action") == "close":
                action = "建议关闭空调"
            elif power is True or str(power).lower() in {"on", "true", "1", "开启"}:
                action = f"空调已经开启，建议调整为{target}℃"
            else:
                action = f"建议打开空调并设置为{target}℃"
            return f"{prefix}；{action}。" if prefix else f"{action}。"
        if state.get("device") == "灯":
            lux = household.data.get("illuminance_lux") if household else None
            brightness = params.get("brightness_percent")
            prefix = (
                f"{room}{'当前' if household and not household.simulated else '估算'}照度约{float(lux):.0f} lx，"
                if isinstance(lux, (int, float))
                else ""
            )
            action = (
                "建议关闭灯光"
                if state.get("action") == "close"
                else f"建议把灯光调整为{brightness}%亮度"
            )
            return f"{prefix}{action}。"
        if state.get("comfort_intent") == "humid":
            return f"{room}湿度偏高，建议开启除湿机。"
        if state.get("comfort_intent") == "dry":
            return f"{room}空气偏干，建议开启加湿器。"
        if state.get("comfort_intent") == "stuffy":
            return f"{room}空气有些闷，建议开启新风。"
        if state.get("comfort_intent") == "air_quality":
            return f"{room}空气质量不佳，建议开启空气净化器。"
        household_summary = household.summary if household else "当前家庭状态暂以可用信息为准"
        return f"{household_summary}；建议执行：{state['request'].transcript}。"

    def _normalize_command(self, transcript: str) -> str:
        command = "".join(str(transcript or "").split())
        candidates = [
            part
            for part in re.split(r"[，,。.!！?？;；：:、]+", command)
            if any(alias in part for alias, _ in _DEVICE_ALIASES)
            and any(action in part for action in _ACTION_WORDS)
        ]
        if candidates:
            command = candidates[-1]
        command = re.sub(r"^(?:天猫管家|天猫智家|智能管家|曼巴管家|管家)[，,：:、]?", "", command)
        command = re.sub(r"^(?:请|麻烦|劳驾|帮我|给我|替我)", "", command)
        command = re.sub(r"^(?:让|叫|请)?天猫精灵(?:帮我|给我|替我)?", "", command)
        command = re.sub(r"^(?:请|麻烦|劳驾|帮我|给我|替我)", "", command)
        return command.strip("，,。.!！?？;；：:、 ")[:120]

    def _replace_evidence(self, items: list[Evidence], item: Evidence) -> list[Evidence]:
        return [existing for existing in items if existing.kind != item.kind] + [item]

    async def _ensure_context_evidence(
        self, state: AgentState, evidence: list[Evidence]
    ) -> list[Evidence]:
        """Guarantee the deterministic fallback still obeys the data-first policy."""
        if not self._data_tools:
            return evidence
        kinds = {item.kind for item in evidence}
        if (
            state.get("device") == "空调"
            or state.get("wellbeing_scenario") in _RELAXATION_SCENARIOS
        ) and "weather" not in kinds:
            evidence = self._replace_evidence(
                evidence, await self._data_tools.get_weather()
            )
            kinds.add("weather")
        if state.get("needs_context") and "household_state" not in kinds:
            evidence = self._replace_evidence(
                evidence,
                await self._data_tools.get_household_state(
                    user_id=state["request"].user_id,
                    room=state.get("room") or self.settings.agent_default_room,
                    memory_context=state["request"].memory_context,
                ),
            )
            kinds.add("household_state")
        household = next(
            (item for item in evidence if item.kind == "household_state"), None
        )
        needs_light_fallback = not self._has_live_illuminance(household)
        if (
            state.get("device") == "灯"
            and needs_light_fallback
            and "environment" not in kinds
        ):
            evidence = self._replace_evidence(
                evidence, await self._data_tools.get_environment()
            )
        return self._prune_redundant_environment(evidence)

    def _missing_required_evidence(
        self, state: AgentState, evidence: list[Evidence]
    ) -> list[str]:
        kinds = {item.kind for item in evidence}
        required = {"household_state"} if state.get("needs_context") else set()
        if (
            state.get("device") == "空调"
            or state.get("wellbeing_scenario") in _RELAXATION_SCENARIOS
        ):
            required.add("weather")
        household = next(
            (item for item in evidence if item.kind == "household_state"), None
        )
        if state.get("device") == "灯" and not self._has_live_illuminance(household):
            required.add("environment")
        return sorted(required - kinds)

    @staticmethod
    def _has_live_illuminance(household: Evidence | None) -> bool:
        if not household:
            return False
        sources = household.data.get("field_sources", {})
        return (
            isinstance(sources, dict)
            and sources.get("illuminance_lux") == "live_sensor"
            and isinstance(household.data.get("illuminance_lux"), (int, float))
        )

    def _prune_redundant_environment(
        self, evidence: list[Evidence]
    ) -> list[Evidence]:
        household = next(
            (item for item in evidence if item.kind == "household_state"), None
        )
        if self._has_live_illuminance(household):
            return [item for item in evidence if item.kind != "environment"]
        return evidence

    def _json_object(self, raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        try:
            parsed = json.loads(raw or "{}")
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def _tool_definitions(self) -> list[dict[str, Any]]:
        plan_schema = ModelPlan.model_json_schema()
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "读取家庭所在地当前天气、体感温度和湿度。",
                    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_environment",
                    "description": "读取当前室内环境模拟值；结果会明确标记为模拟，不能当成传感器实测。",
                    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_household_state",
                    "description": "读取指定房间的实时室温、湿度、照度、占用状态、设备状态、当前时间段和账号温度偏好；缺少传感器时会逐字段标记模拟来源。",
                    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "submit_home_plan",
                    "description": "提交唯一的最终低风险家居控制计划。",
                    "parameters": plan_schema,
                },
            },
        ]

    @staticmethod
    def _wellbeing_tool_definition() -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "submit_wellbeing_advice",
                "description": "提交不触发设备操作的最终生活状态建议。",
                "parameters": WellbeingAdvice.model_json_schema(),
            },
        }
