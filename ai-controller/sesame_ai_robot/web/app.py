from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .errors import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    web_service_exception_handler,
)
from .routes import create_router
from .security import DEFAULT_ALLOWED_ORIGINS, MAX_BODY_BYTES, safe_error
from .service import RobotSimulatorService, WebServiceError, create_service


def create_app(
    *,
    service: RobotSimulatorService | None = None,
    service_factory: Callable[[], RobotSimulatorService] | None = None,
    allowed_origins: tuple[str, ...] = DEFAULT_ALLOWED_ORIGINS,
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

    @app.middleware("http")
    async def enforce_request_limits(request: Request, call_next):
        content_type = request.headers.get("content-type", "")
        size = request.headers.get("content-length")
        has_body = size is not None and size != "0"
        if request.method in {"POST", "PUT", "PATCH"} and has_body and "application/json" not in content_type.lower():
            return JSONResponse(safe_error("invalid_request", "请求必须使用 JSON。"), status_code=415)
        if size is not None:
            try:
                if int(size) > MAX_BODY_BYTES:
                    return JSONResponse(safe_error("request_too_large", "请求体过大。"), status_code=413)
            except ValueError:
                return JSONResponse(safe_error("invalid_request", "请求未通过校验。"), status_code=400)
        return await call_next(request)

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
