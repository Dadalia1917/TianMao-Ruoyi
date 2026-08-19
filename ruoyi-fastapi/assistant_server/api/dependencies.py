from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..core.config import Settings
from ..core.container import ApplicationServices

bearer_scheme = HTTPBearer(auto_error=False)


def get_services(request: Request) -> ApplicationServices:
    return request.app.state.services


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_authenticated_user(
    services: Annotated[ApplicationServices, Depends(get_services)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    token = ""
    if credentials and credentials.scheme.casefold() == "bearer":
        token = credentials.credentials.strip()
    return await services.authenticator.authenticate(token)


ServicesDep = Annotated[ApplicationServices, Depends(get_services)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
CurrentUser = Annotated[str, Depends(get_authenticated_user)]
