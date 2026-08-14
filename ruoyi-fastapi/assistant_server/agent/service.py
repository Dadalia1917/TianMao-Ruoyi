from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Literal, TypedDict
from zoneinfo import ZoneInfo

import httpx
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from ..config import Settings
from .prompts import HOUSEHOLD_AGENT_PROMPT, build_user_prompt
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
)
from .tools import HouseholdDataTools
from .state import HouseholdStateStore

logger = logging.getLogger(__name__)


_DEVICE_ALIASES: tuple[tuple[str, str], ...] = (
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
    "打开", "开启", "启动", "关闭", "关掉", "停止", "调到", "调成", "设为", "设置为",
    "升高", "降低", "调高", "调低", "调亮", "调暗", "调大", "调小", "提高", "减小",
    "切换", "拉开", "拉上", "合上", "清扫", "扫地", "回充", "开", "关",
)
_COMFORT_PATTERNS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("hot", ("有点热", "好热", "太热", "很热", "闷热", "有点闷", "热死了"), "空调"),
    ("cold", ("有点冷", "好冷", "太冷", "很冷", "冻死了"), "空调"),
    ("dark", ("有点暗", "太暗", "好暗", "看不清", "屋里黑", "房间黑"), "灯"),
    ("humid", ("有点潮", "太潮", "好潮", "湿气重", "太湿了"), "除湿机"),
    ("dry", ("有点干", "太干", "好干", "空气干燥"), "加湿器"),
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
    route: Literal["not_applicable", "blocked", "clarify", "direct", "contextual"]
    evidence: list[Evidence]
    model_plan: ModelPlan
    used_function_calling: bool
    comfort_intent: str
    decision: AgentDecision


class HouseholdAgentService:
    """Single orchestrator with bounded tools and deterministic safety gates."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enabled = settings.agent_enabled
        self.ready = False
        self._client: httpx.AsyncClient | None = None
        self._data_tools: HouseholdDataTools | None = None
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
            },
        )
        graph.add_edge("blocked", END)
        graph.add_edge("clarify", END)
        graph.add_edge("not_applicable", END)
        graph.add_edge("direct_plan", "validate")
        graph.add_edge("context_plan", "validate")
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
        if self._comfort_intent(text):
            if any(marker in text for marker in _NEGATIONS):
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
        if any(marker in text for marker in _UNSAFE):
            return {"route": "blocked", "risk_level": RiskLevel.L4}
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
        device = next((canonical for alias, canonical in _DEVICE_ALIASES if alias in text), "")
        if not device or not self.might_be_home_request(text):
            return {"route": "not_applicable", "device": device}
        room = next((name for name in _ROOMS if name in text), "")
        if "开关" in text and not any(word in text for word in ("打开", "开启", "关闭", "关掉")):
            return {"route": "clarify", "device": device, "room": room}
        if any(word in text for word in ("关闭", "关掉", "停止")):
            action = "close"
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
                    "temperature": 0.1,
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

    def _validate(self, state: AgentState) -> dict[str, Any]:
        plan = state["model_plan"]
        device = state["device"]
        planned_device = next(
            (
                canonical
                for alias, canonical in _DEVICE_ALIASES
                if alias in plan.device or alias in plan.command
            ),
            "",
        )
        if any(marker in plan.command for marker in _UNSAFE) or (
            planned_device and planned_device != device
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
        command = self._enforce_recommended_command(state, plan.command, parameters)
        action = DeviceAction(
            command=command,
            device=device,
            room=state.get("room", ""),
            action=state["action"],
            parameters=parameters,
            action_level=ActionLevel.A2 if device in {"空调", "灯"} else ActionLevel.A1,
            risk_level=state.get("risk_level", RiskLevel.L1),
            requires_confirmation=True,
        )
        return {
            "decision": self._base_decision(
                state,
                status=DecisionStatus.EXECUTE,
                user_message=self._contextual_user_message(
                    state, state.get("evidence", []), parameters
                ),
                rationale=plan.rationale,
                action=action,
            )
        }

    def _fallback_context_plan(
        self, state: AgentState, evidence: list[Evidence]
    ) -> dict[str, Any]:
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
            brightness = self._recommended_brightness(lux)
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

    def _command_from_parts(
        self, state: AgentState, params: dict[str, Any], room_device: str
    ) -> str:
        action = state["action"]
        if action == "close":
            return f"关闭{room_device}"
        if state["device"] == "空调" and "temperature_c" in params:
            return f"打开{room_device}并设置为{params['temperature_c']}度"
        if state["device"] == "灯" and "brightness_percent" in params:
            return f"打开{room_device}并调到{params['brightness_percent']}%亮度"
        return self._normalize_command(state["request"].transcript)

    def _enforce_recommended_command(
        self, state: AgentState, command: str, params: dict[str, Any]
    ) -> str:
        room_device = f"{state.get('room', '')}{state['device']}"
        if state["action"] == "close":
            return f"关闭{room_device}"
        if state["device"] == "空调" and "temperature_c" in params:
            return f"打开{room_device}并设置为{params['temperature_c']}度"
        if state["device"] == "灯" and "brightness_percent" in params:
            return f"打开{room_device}并调到{params['brightness_percent']}%亮度"
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
        for mode in ("制冷", "制热", "除湿", "送风", "自动"):
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
        if state.get("device") == "空调" and "weather" not in kinds:
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
        if state.get("device") == "灯" and "environment" not in kinds:
            evidence = self._replace_evidence(
                evidence, await self._data_tools.get_environment()
            )
        return evidence

    def _missing_required_evidence(
        self, state: AgentState, evidence: list[Evidence]
    ) -> list[str]:
        kinds = {item.kind for item in evidence}
        required = {"household_state"} if state.get("needs_context") else set()
        if state.get("device") == "空调":
            required.add("weather")
        if state.get("device") == "灯":
            required.add("environment")
        return sorted(required - kinds)

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
