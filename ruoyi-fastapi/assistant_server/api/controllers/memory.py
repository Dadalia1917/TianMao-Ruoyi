from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ..dependencies import CurrentUser, ServicesDep

router = APIRouter(prefix="/memories", tags=["memory"])


@router.get("")
async def list_memories(services: ServicesDep, user_id: CurrentUser) -> dict[str, Any]:
    items = await services.memory.list_memories(user_id)
    return {"items": items, "count": len(items)}


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: int, services: ServicesDep, user_id: CurrentUser
) -> dict[str, bool]:
    deleted = await services.memory.delete_memory(user_id, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="记忆不存在或已删除")
    return {"deleted": True}


@router.delete("")
async def clear_memories(services: ServicesDep, user_id: CurrentUser) -> dict[str, int]:
    deleted = await services.memory.clear_memories(user_id)
    return {"deleted": deleted}
