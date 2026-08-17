from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol, runtime_checkable

from .schemas import RiskLevel


DEVICE_ALIASES: tuple[tuple[str, str], ...] = (
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
ROOMS = (
    "主卧", "次卧", "儿童房", "老人房", "客厅", "卧室", "书房", "厨房",
    "餐厅", "卫生间", "浴室", "阳台", "玄关", "全屋",
)
UNSAFE_MARKERS = (
    "门锁", "开锁", "燃气", "燃气灶", "灶具", "电磁炉", "烤箱", "微波炉",
    "热水器", "车库门", "监控", "摄像头", "撤防", "报警器", "电热毯", "取暖器",
)
NEGATIONS = ("不要", "别", "不用", "取消", "不需要")
DISCUSSION_MARKERS = (
    "怎么", "如何", "为什么", "方法", "教程", "原理", "区别", "开了吗", "关了吗",
    "开着吗", "关着吗", "亮着吗", "有没有开", "有没有关", "设备状态",
    "我刚才说", "比如", "例如", "能不能控制", "可不可以控制",
)
ACTION_WORDS = (
    "播放", "来一首", "放一首", "听",
    "打开", "开启", "启动", "关闭", "关掉", "停止", "调到", "调成", "设为", "设置为",
    "升高", "降低", "调高", "调低", "调亮", "调暗", "调大", "调小", "提高", "减小",
    "切换", "拉开", "拉上", "合上", "清扫", "扫地", "回充", "开", "关",
)
COMFORT_PATTERNS: tuple[tuple[str, tuple[str, ...], str], ...] = (
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
WELLBEING_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("fatigue", ("我累了", "有点累", "好累", "太累", "很疲惫", "有点疲惫", "精疲力尽")),
    ("sleepy", ("我困了", "有点困", "好困", "太困", "困死了", "想睡觉", "犯困")),
    ("sleep_problem", ("睡不着", "失眠了", "一直没睡着", "难以入睡")),
    ("stress", ("压力很大", "压力好大", "有点焦虑", "很焦虑", "心里很烦", "好烦", "太烦了", "很烦躁", "想放松", "我想放松一下")),
    ("thirst", ("我渴了", "有点渴", "好渴", "口渴")),
    ("hunger", ("我饿了", "有点饿", "好饿", "肚子饿")),
    ("headache", ("有点头疼", "有点头痛", "头有点晕", "轻微头晕")),
    ("noise", ("太吵了", "有点吵", "噪音好大", "声音太吵")),
)
RELAXATION_SCENARIOS = frozenset({"fatigue", "stress"})
RELAXATION_DEVICES = ("空调", "风扇", "音乐播放器")
HEALTH_ALERTS = (
    "胸痛", "胸口剧痛", "呼吸困难", "喘不上气", "无法呼吸", "昏倒", "昏厥",
    "意识不清", "严重过敏", "嘴唇发紫", "突然说不清话", "一侧无力",
)
NEGATED_FEELINGS = (
    "不热", "不冷", "不累", "不困", "不渴", "不饿", "不焦虑", "不烦",
    "没有压力", "没那么累", "没那么困", "没事",
)


def find_comfort_intent(text: str) -> str:
    for name, markers, _device in COMFORT_PATTERNS:
        if any(marker in text for marker in markers):
            return name
    return ""


def find_wellbeing_scenario(text: str) -> str:
    for name, markers in WELLBEING_PATTERNS:
        if any(marker in text for marker in markers):
            return name
    return ""


def _room(text: str, fallback: str = "") -> str:
    return next((name for name in ROOMS if name in text), fallback)


def _device(text: str) -> str:
    return next(
        (canonical for alias, canonical in DEVICE_ALIASES if alias in text),
        "",
    )


def _is_explicit_device_request(text: str) -> bool:
    has_device = bool(_device(text)) or any(marker in text for marker in UNSAFE_MARKERS)
    has_action = any(marker in text for marker in ACTION_WORDS)
    if not text or not has_device or not has_action:
        return False
    if any(marker in text for marker in NEGATIONS):
        return False
    return not any(marker in text for marker in DISCUSSION_MARKERS)


@dataclass(frozen=True)
class IntentContext:
    text: str
    default_room: str


@runtime_checkable
class IntentHandler(Protocol):
    """Small, ordered intent plug-in used before the fixed LangGraph planner."""

    name: str
    priority: int

    def matches(self, context: IntentContext) -> bool: ...

    def accepts_as_entrypoint(self, context: IntentContext) -> bool: ...

    def analyze(self, context: IntentContext) -> dict[str, Any]: ...


class IntentHandlerRegistry:
    """Copy-on-write priority registry so startup plug-ins are deterministic."""

    def __init__(self, handlers: Iterable[IntentHandler] = ()) -> None:
        self._handlers: tuple[IntentHandler, ...] = ()
        for handler in handlers:
            self.register(handler)

    @property
    def handlers(self) -> tuple[IntentHandler, ...]:
        return self._handlers

    def register(self, handler: IntentHandler, *, replace: bool = False) -> None:
        if not isinstance(handler, IntentHandler):
            raise TypeError("intent handler must implement the IntentHandler protocol")
        name = str(handler.name or "").strip()
        if not name:
            raise ValueError("intent handler name is required")
        existing = next((item for item in self._handlers if item.name == name), None)
        if existing is not None and not replace:
            raise ValueError(f"intent handler already registered: {name}")
        items = [item for item in self._handlers if item.name != name]
        items.append(handler)
        self._handlers = tuple(
            sorted(items, key=lambda item: (-int(item.priority), item.name))
        )

    def resolve(self, context: IntentContext) -> dict[str, Any]:
        for handler in self._handlers:
            if handler.matches(context):
                return handler.analyze(context)
        raise RuntimeError("intent registry has no fallback handler")

    def accepts_as_entrypoint(self, context: IntentContext) -> bool:
        return any(
            handler.accepts_as_entrypoint(context) for handler in self._handlers
        )

    def catalog(self) -> list[dict[str, Any]]:
        return [
            {"name": handler.name, "priority": int(handler.priority)}
            for handler in self._handlers
        ]


class HealthAlertIntentHandler:
    name = "health_alert"
    priority = 1000

    def matches(self, context: IntentContext) -> bool:
        return any(marker in context.text for marker in HEALTH_ALERTS)

    def accepts_as_entrypoint(self, context: IntentContext) -> bool:
        return self.matches(context)

    def analyze(self, context: IntentContext) -> dict[str, Any]:
        return {
            "route": "health_notice",
            "risk_level": RiskLevel.L4,
            "wellbeing_scenario": "health_alert",
        }


class UnsafeDeviceIntentHandler:
    name = "unsafe_device"
    priority = 900

    def matches(self, context: IntentContext) -> bool:
        return any(marker in context.text for marker in UNSAFE_MARKERS)

    def accepts_as_entrypoint(self, context: IntentContext) -> bool:
        return self.matches(context) and _is_explicit_device_request(context.text)

    def analyze(self, context: IntentContext) -> dict[str, Any]:
        return {"route": "blocked", "risk_level": RiskLevel.L4}


class RelaxationIntentHandler:
    name = "relaxation"
    priority = 800

    def matches(self, context: IntentContext) -> bool:
        return find_wellbeing_scenario(context.text) in RELAXATION_SCENARIOS

    def accepts_as_entrypoint(self, context: IntentContext) -> bool:
        return self.matches(context) and not any(
            marker in context.text for marker in NEGATED_FEELINGS
        )

    def analyze(self, context: IntentContext) -> dict[str, Any]:
        return {
            "route": "contextual",
            "device": "",
            "room": _room(context.text, context.default_room),
            "action": "recommend",
            "risk_level": RiskLevel.L2,
            "needs_context": True,
            "comfort_intent": "relax",
            "wellbeing_scenario": find_wellbeing_scenario(context.text),
            "allowed_devices": RELAXATION_DEVICES,
        }


class ComfortIntentHandler:
    name = "comfort"
    priority = 700

    def matches(self, context: IntentContext) -> bool:
        return bool(find_comfort_intent(context.text))

    def accepts_as_entrypoint(self, context: IntentContext) -> bool:
        return (
            self.matches(context)
            and not any(marker in context.text for marker in NEGATIONS + NEGATED_FEELINGS)
            and not any(marker in context.text for marker in DISCUSSION_MARKERS)
        )

    def analyze(self, context: IntentContext) -> dict[str, Any]:
        comfort_intent = find_comfort_intent(context.text)
        device = next(
            device
            for name, _markers, device in COMFORT_PATTERNS
            if name == comfort_intent
        )
        return {
            "route": "contextual",
            "device": device,
            "room": _room(context.text, context.default_room),
            "action": "set" if device in {"空调", "灯"} else "open",
            "risk_level": RiskLevel.L2 if device == "空调" else RiskLevel.L1,
            "needs_context": True,
            "comfort_intent": comfort_intent,
        }


class WellbeingIntentHandler:
    name = "wellbeing"
    priority = 600

    def matches(self, context: IntentContext) -> bool:
        return bool(find_wellbeing_scenario(context.text))

    def accepts_as_entrypoint(self, context: IntentContext) -> bool:
        return self.matches(context) and not any(
            marker in context.text for marker in NEGATED_FEELINGS
        )

    def analyze(self, context: IntentContext) -> dict[str, Any]:
        return {
            "route": "wellbeing",
            "risk_level": RiskLevel.L0,
            "needs_context": True,
            "wellbeing_scenario": find_wellbeing_scenario(context.text),
            "room": _room(context.text, context.default_room),
        }


class DeviceControlIntentHandler:
    name = "device_control"
    priority = 500

    def matches(self, context: IntentContext) -> bool:
        return bool(_device(context.text)) and _is_explicit_device_request(context.text)

    def accepts_as_entrypoint(self, context: IntentContext) -> bool:
        return self.matches(context)

    def analyze(self, context: IntentContext) -> dict[str, Any]:
        text = context.text
        device = _device(text)
        room = _room(text)
        if "开关" in text and not any(
            word in text for word in ("打开", "开启", "关闭", "关掉")
        ):
            return {"route": "clarify", "device": device, "room": room}
        if any(word in text for word in ("关闭", "关掉", "停止")):
            action = "close"
        elif any(word in text for word in ("播放", "来一首", "放一首", "听")):
            action = "play"
        elif "回充" in text:
            action = "dock"
        elif any(word in text for word in ("清扫", "扫地")):
            action = "clean"
        elif any(
            word in text
            for word in ("调到", "调成", "设为", "设置为", "调高", "调低", "调亮", "调暗")
        ):
            action = "set"
        elif any(word in text for word in ("打开", "开启", "启动", "开")):
            action = "open"
        else:
            action = "set"
        return {
            "route": "contextual",
            "device": device,
            "room": room,
            "action": action,
            "risk_level": RiskLevel.L2 if device == "空调" else RiskLevel.L1,
            "needs_context": True,
        }


class NotApplicableIntentHandler:
    name = "not_applicable"
    priority = -1000

    def matches(self, context: IntentContext) -> bool:
        return True

    def accepts_as_entrypoint(self, context: IntentContext) -> bool:
        return False

    def analyze(self, context: IntentContext) -> dict[str, Any]:
        return {"route": "not_applicable", "device": _device(context.text)}


def default_intent_handlers() -> tuple[IntentHandler, ...]:
    return (
        HealthAlertIntentHandler(),
        UnsafeDeviceIntentHandler(),
        RelaxationIntentHandler(),
        ComfortIntentHandler(),
        WellbeingIntentHandler(),
        DeviceControlIntentHandler(),
        NotApplicableIntentHandler(),
    )
