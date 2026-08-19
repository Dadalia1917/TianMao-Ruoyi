"""ASGI compatibility entrypoint for local and container deployments."""

from __future__ import annotations

import uvicorn

from assistant_server import APP_VERSION as _APP_VERSION
from assistant_server.application import PROJECT_DIR, create_app

APP_VERSION = _APP_VERSION
BASE_DIR = PROJECT_DIR
app = create_app()
settings = app.state.settings


if __name__ == "__main__":
    # Passing the app object avoids importing this module a second time locally.
    # Production can continue to run ``uvicorn main:app`` with multiple workers.
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=False,
    )
