from __future__ import annotations

import asyncio
import math
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from .schemas import Evidence


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
    ) -> None:
        self.client = client
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = timezone
        self.location_name = location_name
        self.weather_enabled = weather_enabled
        self.simulated_environment_enabled = simulated_environment_enabled
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
