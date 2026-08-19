from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ..dependencies import CurrentUser, ServicesDep

router = APIRouter(tags=["text-chat"])


@router.get("/text-models")
async def text_models(services: ServicesDep, _user_id: CurrentUser) -> dict[str, Any]:
    items = services.text_chat.model_catalog()
    return {"items": items, "count": len(items)}
