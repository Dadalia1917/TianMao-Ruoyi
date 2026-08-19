from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI

from . import APP_NAME, APP_VERSION
from .api import api_router
from .core.config import Settings, load_local_env
from .core.exceptions import register_exception_handlers
from .core.lifecycle import create_lifespan
from .core.middleware import register_middleware

PROJECT_DIR = Path(__file__).resolve().parent.parent


def load_settings() -> Settings:
    """Load the checked-in local defaults without overriding process secrets."""
    load_local_env(PROJECT_DIR / ".env")
    return Settings.from_env()


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create one independently configurable FastAPI application."""
    app_settings = settings or load_settings()
    configure_logging(app_settings)
    app = FastAPI(
        title=APP_NAME,
        description="天猫智家实时语音、文字对话、长期记忆与家庭 Agent API",
        version=APP_VERSION,
        docs_url="/docs",
        redoc_url=None,
        lifespan=create_lifespan(app_settings),
    )
    app.state.settings = app_settings
    register_middleware(app, app_settings)
    register_exception_handlers(app)
    app.include_router(api_router)
    return app
