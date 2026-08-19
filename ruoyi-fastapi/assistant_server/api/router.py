from fastapi import APIRouter

from .controllers import agent, memory, system, text_chat, websockets

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(memory.router, prefix="/api/v1")
api_router.include_router(text_chat.router, prefix="/api/v1")
api_router.include_router(agent.router, prefix="/api/v1")
api_router.include_router(websockets.router)
