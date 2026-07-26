from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .security import safe_error
from .service import WebServiceError


def error_response(code: str, message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(safe_error(code, message), status_code=status_code)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response("invalid_request", "请求未通过校验。", 422)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = "not_found" if exc.status_code == 404 else "invalid_request"
    message = "请求的 API 不存在。" if exc.status_code == 404 else "请求未通过校验。"
    return error_response(code, message, exc.status_code)


async def web_service_exception_handler(request: Request, exc: WebServiceError) -> JSONResponse:
    status = 404 if exc.code == "unknown_fault" else 400
    return error_response(exc.code, exc.message, status)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response("internal_error", "服务处理请求失败。", 500)
