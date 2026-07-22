from __future__ import annotations

import re
from typing import Any


FORBIDDEN_MEMORY_FIELDS = {
    "api_key",
    "apikey",
    "secret_key",
    "token",
    "access_token",
    "refresh_token",
    "password",
    "passwd",
    "confirmation_id",
    "confirmationid",
    "system_prompt",
    "systemprompt",
    "safety_override",
    "safetyoverride",
    "bypass_arbiter",
    "skip_arbiter",
}
FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}\b"),
    re.compile(r"\b(api[_-]?key|token|password|confirmation[_-]?id)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\b(system\s+prompt|safety\s+override|bypass\s+arbiter|skip\s+arbiter)\b", re.IGNORECASE),
)
MAX_MEMORY_STRING_CHARS = 500


def sanitize_memory_value(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, child in value.items():
            key_text = str(key)
            if _is_forbidden_key(key_text):
                continue
            cleaned[key_text[:80]] = sanitize_memory_value(child)
        return cleaned
    if isinstance(value, list):
        return [sanitize_memory_value(item) for item in value[:50]]
    if isinstance(value, tuple):
        return tuple(sanitize_memory_value(item) for item in value[:50])
    if isinstance(value, str):
        return _sanitize_text(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:MAX_MEMORY_STRING_CHARS]


def memory_key_allowed(key: str) -> bool:
    return not _is_forbidden_key(key)


def _is_forbidden_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", key.lower())
    return any(re.sub(r"[^a-z0-9]", "", field) in normalized for field in FORBIDDEN_MEMORY_FIELDS)


def _sanitize_text(text: str) -> str:
    sanitized = text[:MAX_MEMORY_STRING_CHARS]
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        sanitized = pattern.sub("[redacted]", sanitized)
    return sanitized
