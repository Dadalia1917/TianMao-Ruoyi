from __future__ import annotations

import asyncio
import math
import re
import time
from datetime import datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

import httpx

from .schemas import Evidence
from .state import HouseholdStateStore

_WEATHER_DESCRIPTIONS = {
    0: "晴",
    1: "大部晴朗",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "强毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    80: "小阵雨",
    81: "阵雨",
    82: "强阵雨",
    95: "雷雨",
    96: "雷雨伴小冰雹",
    99: "雷雨伴冰雹",
}


class HouseholdDataTools:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        latitude: float,
        longitude: float,
        timezone: str,
        location_name: str,
        weather_enabled: bool,
        simulated_environment_enabled: bool,
        state_store: HouseholdStateStore,
    ) -> None:
        self.client = client
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = timezone
        self.location_name = location_name
        self.weather_enabled = weather_enabled
        self.simulated_environment_enabled = simulated_environment_enabled
        self.state_store = state_store
        self._weather_cache: tuple[float, Evidence] | None = None
        self._weather_lock = asyncio.Lock()

    def _now(self) -> datetime:
        try:
            return datetime.now(ZoneInfo(self.timezone))
        except Exception:
            return datetime.now().astimezone()

    async def get_weather(self) -> Evidence:
        if not self.weather_enabled:
            return Evidence(
                kind="weather",
                summary="天气数据功能未启用",
                source="configuration",
                observed_at=self._now(),
                reliability="unavailable",
            )
        cached = self._weather_cache
        if cached and time.monotonic() - cached[0] < 300:
            return cached[1].model_copy(deep=True)
        async with self._weather_lock:
            cached = self._weather_cache
            if cached and time.monotonic() - cached[0] < 300:
                return cached[1].model_copy(deep=True)
            try:
                response = await self.client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": self.latitude,
                        "longitude": self.longitude,
                        "current": (
                            "temperature_2m,apparent_temperature,"
                            "relative_humidity_2m,weather_code,is_day,wind_speed_10m"
                        ),
                        "daily": "temperature_2m_max,temperature_2m_min,weather_code",
                        "forecast_days": 1,
                        "timezone": self.timezone,
                    },
                    timeout=6,
                )
                response.raise_for_status()
                payload = response.json()
                current = payload.get("current") or {}
                daily = payload.get("daily") or {}
                code = int(current.get("weather_code", -1))
                temperature = float(current["temperature_2m"])
                apparent = float(current.get("apparent_temperature", temperature))
                humidity = int(current.get("relative_humidity_2m", 0))
                summary = (
                    f"{self.location_name}当前{_WEATHER_DESCRIPTIONS.get(code, '天气代码' + str(code))}，"
                    f"{temperature:.1f}℃，体感{apparent:.1f}℃，湿度{humidity}%"
                )
                evidence = Evidence(
                    kind="weather",
                    summary=summary,
                    source="Open-Meteo Forecast API",
                    observed_at=self._now(),
                    reliability="high",
                    data={
                        "location": self.location_name,
                        "temperature_c": temperature,
                        "apparent_temperature_c": apparent,
                        "humidity_percent": humidity,
                        "weather_code": code,
                        "weather": _WEATHER_DESCRIPTIONS.get(code, str(code)),
                        "is_day": bool(current.get("is_day", 1)),
                        "wind_speed_kmh": current.get("wind_speed_10m"),
                        "daily_max_c": (daily.get("temperature_2m_max") or [None])[0],
                        "daily_min_c": (daily.get("temperature_2m_min") or [None])[0],
                    },
                )
                self._weather_cache = (time.monotonic(), evidence)
                return evidence.model_copy(deep=True)
            except Exception as exc:
                return Evidence(
                    kind="weather",
                    summary="天气服务暂时不可用，当前天气未知",
                    source="Open-Meteo Forecast API",
                    observed_at=self._now(),
                    reliability="unavailable",
                    data={"error": type(exc).__name__},
                )

    async def get_environment(self) -> Evidence:
        if not self.simulated_environment_enabled:
            return Evidence(
                kind="environment",
                summary="未接入室内环境传感器",
                source="configuration",
                observed_at=self._now(),
                reliability="unavailable",
            )
        now = self._now()
        hour = now.hour + now.minute / 60
        # 平滑的昼夜照度曲线只用于联调；明确标记为模拟，后续可替换 Home Assistant。
        daylight = max(0.0, math.sin(math.pi * (hour - 6) / 13))
        estimated_lux = int(25 + 875 * daylight)
        weather = await self.get_weather()
        outside = weather.data.get("temperature_c")
        indoor = None
        if isinstance(outside, (int, float)):
            indoor = round(max(17.0, min(31.0, 21.5 + (outside - 21.5) * 0.35)), 1)
        data: dict[str, Any] = {
            "illuminance_lux": estimated_lux,
            "sensor_mode": "simulation",
            "basis": "local_time_daylight_curve",
        }
        if indoor is not None:
            data["estimated_indoor_temperature_c"] = indoor
        summary = f"模拟室内照度约{estimated_lux} lx"
        if indoor is not None:
            summary += f"，模拟室温约{indoor:.1f}℃"
        return Evidence(
            kind="environment",
            summary=summary + "（非传感器实测）",
            source="Tmall Smart Home environment simulator",
            observed_at=now,
            reliability="low",
            simulated=True,
            data=data,
        )

    async def get_household_state(
        self,
        *,
        user_id: str,
        room: str,
        memory_context: str = "",
    ) -> Evidence:
        """Build the decision snapshot from live telemetry plus explicit fallbacks."""
        now = self._now()
        live = await self.state_store.get(user_id, room)
        environment = await self.get_environment()
        live_is_fresh = bool(live and live.fresh)
        field_sources: dict[str, str] = {}

        def live_value(name: str) -> Any:
            if live_is_fresh:
                value = getattr(live, name)
                if value is not None:
                    field_sources[name] = "live_sensor"
                    return value
            return None

        indoor_temperature = live_value("indoor_temperature_c")
        indoor_humidity = live_value("indoor_humidity_percent")
        illuminance = live_value("illuminance_lux")
        occupancy = live_value("occupancy")
        if indoor_temperature is None:
            indoor_temperature = environment.data.get("estimated_indoor_temperature_c")
            if indoor_temperature is not None:
                field_sources["indoor_temperature_c"] = "simulation"
        if illuminance is None:
            illuminance = environment.data.get("illuminance_lux")
            if illuminance is not None:
                field_sources["illuminance_lux"] = "simulation"
        if indoor_humidity is None:
            # Until a sensor is connected, use a neutral commissioning value and label it.
            indoor_humidity = 55
            field_sources["indoor_humidity_percent"] = "simulation"
        if occupancy is None:
            occupancy = True
            field_sources["occupancy"] = "request_context"

        preferred_temperature = self._preferred_temperature(memory_context)
        period = self._time_period(now.hour)
        devices = dict(live.device_states) if live_is_fresh and live else {}
        if "空调" not in devices:
            devices["空调"] = {"power": "unknown"}
        if "灯" not in devices:
            devices["灯"] = {"power": "unknown"}

        data: dict[str, Any] = {
            "room": room,
            "indoor_temperature_c": indoor_temperature,
            "indoor_humidity_percent": indoor_humidity,
            "illuminance_lux": illuminance,
            "occupancy": occupancy,
            "device_states": devices,
            "local_time": now.isoformat(),
            "time_period": period,
            "preferred_temperature_c": preferred_temperature,
            "field_sources": field_sources,
            "live_state_fresh": live_is_fresh,
        }
        parts = [f"{room}{period}"]
        if indoor_temperature is not None:
            prefix = (
                "实测" if field_sources.get("indoor_temperature_c") == "live_sensor" else "模拟"
            )
            parts.append(f"{prefix}室温{float(indoor_temperature):.1f}℃")
        if indoor_humidity is not None:
            prefix = (
                "实测" if field_sources.get("indoor_humidity_percent") == "live_sensor" else "模拟"
            )
            parts.append(f"{prefix}湿度{float(indoor_humidity):.0f}%")
        if illuminance is not None:
            prefix = "实测" if field_sources.get("illuminance_lux") == "live_sensor" else "模拟"
            parts.append(f"{prefix}照度{float(illuminance):.0f} lx")
        if preferred_temperature is not None:
            parts.append(f"账号偏好{preferred_temperature}℃")
        reliability: Literal["high", "low"] = "high" if live_is_fresh else "low"
        source = live.source if live_is_fresh and live else "household-state fallback simulator"
        return Evidence(
            kind="household_state",
            summary="，".join(parts) + ("" if live_is_fresh else "（缺少实时传感器上报）"),
            source=source,
            observed_at=live.observed_at if live_is_fresh and live else now,
            reliability=reliability,
            simulated=not live_is_fresh,
            data=data,
        )

    @staticmethod
    def _preferred_temperature(memory_context: str) -> int | None:
        patterns = (
            r"(?:偏好|喜欢|习惯|通常|平时|常用).{0,18}?(1[6-9]|2\d|30)\s*(?:摄氏)?度",
            r"(1[6-9]|2\d|30)\s*(?:摄氏)?度.{0,12}?(?:最舒服|舒适|合适)",
        )
        for pattern in patterns:
            match = re.search(pattern, memory_context or "")
            if match:
                return max(16, min(30, int(match.group(1))))
        return None

    @staticmethod
    def _time_period(hour: int) -> str:
        if 5 <= hour < 9:
            return "清晨"
        if 9 <= hour < 12:
            return "上午"
        if 12 <= hour < 14:
            return "中午"
        if 14 <= hour < 18:
            return "下午"
        if 18 <= hour < 23:
            return "晚上"
        return "深夜"
