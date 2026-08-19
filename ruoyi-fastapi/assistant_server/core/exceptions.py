from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..services.authentication import AuthenticationError


def register_exception_handlers(app: FastAPI) -> None:
    """Register application exceptions without exposing internal failures."""

    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(
        _request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})
