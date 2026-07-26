from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from .security import MAX_BODY_BYTES, is_json_content_type, safe_error


ASGIApp = Callable[[dict[str, Any], Callable[[], Awaitable[dict[str, Any]]], Callable[[dict[str, Any]], Awaitable[None]]], Awaitable[None]]


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, *, max_body_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                if int(content_length.decode("ascii")) > self.max_body_bytes:
                    await _send_json(send, 413, safe_error("request_too_large", "请求体过大。"))
                    return
            except ValueError:
                await _send_json(send, 400, safe_error("invalid_request", "请求未通过校验。"))
                return

        chunks: list[bytes] = []
        total = 0
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] != "http.request":
                continue
            body = message.get("body", b"")
            if body:
                total += len(body)
                if total > self.max_body_bytes:
                    await _send_json(send, 413, safe_error("request_too_large", "请求体过大。"))
                    return
                chunks.append(body)
            more_body = bool(message.get("more_body", False))

        body = b"".join(chunks)
        method = scope.get("method", "").upper()
        content_type = headers.get(b"content-type")
        content_type_text = content_type.decode("latin1") if content_type is not None else ""
        if method in {"POST", "PUT", "PATCH"} and body and not is_json_content_type(content_type_text):
            await _send_json(send, 415, safe_error("invalid_request", "请求必须使用 JSON。"))
            return

        delivered = False

        async def replay_receive():
            nonlocal delivered
            if delivered:
                return {"type": "http.request", "body": b"", "more_body": False}
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay_receive, send)


async def _send_json(send, status_code: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": status_code,
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
        ],
    })
    await send({"type": "http.response.body", "body": body, "more_body": False})
