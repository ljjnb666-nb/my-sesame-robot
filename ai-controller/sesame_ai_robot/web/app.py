from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .body_limit import BodyLimitMiddleware
from .errors import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    web_service_exception_handler,
)
from .routes import create_router
from .security import DEFAULT_ALLOWED_HOSTS, DEFAULT_ALLOWED_ORIGINS
from .service import RobotSimulatorService, WebServiceError, create_service


def create_app(
    *,
    service: RobotSimulatorService | None = None,
    service_factory: Callable[[], RobotSimulatorService] | None = None,
    allowed_origins: tuple[str, ...] = DEFAULT_ALLOWED_ORIGINS,
    allowed_hosts: tuple[str, ...] = DEFAULT_ALLOWED_HOSTS,
) -> FastAPI:
    app = FastAPI(title="Sesame Web Simulator API", version="0.4")
    app.state.service = service
    app.state.service_factory = service_factory or create_service

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(allowed_hosts))
    app.add_middleware(BodyLimitMiddleware)

    def get_service() -> RobotSimulatorService:
        if app.state.service is None:
            app.state.service = app.state.service_factory()
        return app.state.service

    app.include_router(create_router(get_service))
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(WebServiceError, web_service_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    return app
