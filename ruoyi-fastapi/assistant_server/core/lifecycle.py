from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import fields

from fastapi import FastAPI

from .. import APP_VERSION
from .config import Settings
from .container import ApplicationServices, create_service_scope

logger = logging.getLogger(__name__)


def _publish_services(app: FastAPI, services: ApplicationServices) -> None:
    """Expose one typed container and keep legacy state attributes compatible."""
    app.state.services = services
    for service_field in fields(services):
        setattr(app.state, service_field.name, getattr(services, service_field.name))


def create_lifespan(
    settings: Settings,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Build a lifespan bound to this application instance's settings."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        validation_errors = settings.validate()
        if validation_errors:
            raise RuntimeError("；".join(validation_errors))

        async with create_service_scope(settings) as services:
            _publish_services(app, services)
            logger.info(
                "assistant server ready: version=%s model=%s api_key=%s "
                "database=%s memory=%s text=%s agent=%s",
                APP_VERSION,
                settings.dashscope_model,
                "configured" if settings.dashscope_api_key else "missing",
                "ready" if services.history.ready else "disabled",
                "ready" if services.memory.ready else "disabled",
                "ready" if services.text_chat.ready else "disabled",
                "ready"
                if services.agent.ready
                else "policy_only"
                if services.agent.enabled
                else "disabled",
            )
            yield

    return lifespan
