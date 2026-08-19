from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ...agent import AgentRequest, HouseholdStateUpdate
from ..dependencies import CurrentUser, ServicesDep, SettingsDep

router = APIRouter(prefix="/agent", tags=["household-agent"])


@router.get("/capabilities")
async def agent_capabilities(
    services: ServicesDep,
    settings: SettingsDep,
    _user_id: CurrentUser,
) -> dict[str, Any]:
    return {
        "enabled": services.agent.enabled,
        "function_calling": services.agent.ready,
        "policy_fallback": True,
        "intent_handlers": services.agent.intent_handler_catalog(),
        "devices": [
            "灯",
            "空调",
            "新风",
            "窗帘",
            "电视",
            "投影仪",
            "风扇",
            "空气净化器",
            "加湿器",
            "除湿机",
            "扫地机器人",
            "智能插座",
        ],
        "context_tools": {
            "weather": settings.agent_weather_enabled,
            "simulated_environment": settings.agent_simulated_environment_enabled,
            "live_household_state": True,
        },
        "household_state_ttl_seconds": settings.agent_household_state_ttl_seconds,
        "default_room": settings.agent_default_room,
        "execution_channel": "android_genie_content_provider",
        "policy_version": "household-agent-1.2.0",
    }


@router.post("/plan")
async def plan_home_action(
    payload: AgentRequest,
    services: ServicesDep,
    user_id: CurrentUser,
) -> dict[str, Any]:
    decision = await services.agent.plan(payload.model_copy(update={"user_id": user_id}))
    services.metrics.inc(f"agent_{decision.status.value}_total")
    return decision.model_dump(mode="json")


@router.put("/household-state/{room}")
async def update_household_state(
    room: str,
    payload: HouseholdStateUpdate,
    services: ServicesDep,
    user_id: CurrentUser,
) -> dict[str, Any]:
    snapshot = await services.agent.update_household_state(user_id, room, payload)
    return snapshot.model_dump(mode="json")


@router.get("/household-state")
async def get_household_state(
    services: ServicesDep,
    settings: SettingsDep,
    user_id: CurrentUser,
    room: str | None = None,
) -> dict[str, Any]:
    selected_room = room or settings.agent_default_room
    snapshot = await services.agent.get_household_state(user_id, selected_room)
    if snapshot is None:
        return {
            "room": selected_room,
            "fresh": False,
            "available": False,
            "message": "尚未收到该房间的实时家庭状态；Agent 将使用明确标记的模拟值。",
        }
    return {"available": True, **snapshot.model_dump(mode="json")}


@router.delete("/household-state")
async def clear_household_state(
    services: ServicesDep,
    user_id: CurrentUser,
    room: str | None = None,
) -> dict[str, Any]:
    deleted = await services.agent.clear_household_state(user_id, room)
    return {"deleted": deleted}
