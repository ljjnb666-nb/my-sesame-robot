from __future__ import annotations

import json
import re
from typing import Any

from ..ai_models import MAX_TEXT_CHARS


API_VERSION = "0.4"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
DEFAULT_WORKERS = 1
DEFAULT_ALLOWED_ORIGINS = ("http://127.0.0.1:5173", "http://localhost:5173")
MAX_BODY_BYTES = 16 * 1024
MAX_CONFIRMATION_ID_CHARS = 128
MAX_FAULT_CHARS = 80
MAX_PATH_CHARS = 120
MAX_TIMELINE_LIMIT = 50
DEFAULT_TIMELINE_LIMIT = 20
CHAT_TEXT_LIMIT = min(MAX_TEXT_CHARS, 500)

FORBIDDEN_REQUEST_FIELDS = {
    "runtimeMode",
    "runtime_mode",
    "allowRealRobot",
    "allow_real_robot",
    "safetySeverity",
    "safety_severity",
    "toolCall",
    "tool_call",
    "confirmationGrant",
    "confirmation_grant",
    "confirmationGrants",
    "confirmation_grants",
}

SENSITIVE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]+"),
    re.compile(r"(?i)(api[_-]?key|authorization|bearer|password|token|secret)=?[^\s,;}]*"),
    re.compile(r"[A-Za-z]:\\[^\s\"']+"),
    re.compile(r"/Users/[^\s\"']+"),
)


def assert_local_host(host: str) -> str:
    normalized = host.strip().lower()
    if normalized not in {"127.0.0.1", "localhost"}:
        raise ValueError("web simulator API is localhost-only")
    return "127.0.0.1" if normalized == "localhost" else normalized


def safe_error(code: str = "invalid_request", message: str = "请求未通过校验。") -> dict[str, Any]:
    return {"error": {"code": code, "message": sanitize_text(message, 240)}}


def sanitize_text(value: Any, limit: int = 500) -> str:
    text = str(value)
    for pattern in SENSITIVE_PATTERNS:
        text = pattern.sub("[filtered]", text)
    text = text.replace("\r", " ").replace("\n", " ")
    return text[:limit]


def sanitize_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            return None
        return value
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_jsonable(item) for item in value[:50]]
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, child in list(value.items())[:80]:
            key_text = str(key)
            normalized = key_text.lower().replace("-", "_")
            if "api_key" in normalized or "authorization" in normalized or "password" in normalized:
                continue
            clean[key_text] = sanitize_jsonable(child)
        return clean
    return "[filtered]"


def ensure_json_safe(payload: Any) -> Any:
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    return json.loads(encoded)
