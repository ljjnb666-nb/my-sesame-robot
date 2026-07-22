from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_PROFILE_PATH = Path(__file__).resolve().parents[1] / "robot_profile.yaml"
FORBIDDEN_PROFILE_KEYS = {
    "arbiter",
    "arbiter_rules",
    "confirmation",
    "confirmation_required",
    "confirmation_requirements",
    "safety",
    "safety_severity",
    "safety_override",
    "runtime_authorized_actions",
    "allow_real_robot",
}


@dataclass(frozen=True)
class RobotProfile:
    name: str = "Sesame Robot"
    capabilities: tuple[str, ...] = ()
    personality: dict[str, Any] | str = ""
    limits: dict[str, Any] | None = None

    def get_capability(self, name: str) -> bool:
        return name in self.capabilities

    def get_personality(self, key: str | None = None) -> Any:
        if key is None:
            return self.personality
        if isinstance(self.personality, dict):
            return self.personality.get(key)
        return self.personality if key == "description" else None


def load_profile(path: str | Path | None = None) -> RobotProfile:
    profile_path = Path(path) if path is not None else DEFAULT_PROFILE_PATH
    if not profile_path.exists():
        return RobotProfile()
    payload = _parse_limited_yaml(profile_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("robot profile root must be a mapping")
    _reject_forbidden_profile_fields(payload)
    allowed = {"name", "capabilities", "personality", "limits"}
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(f"unknown robot profile fields: {sorted(unknown)}")
    capabilities = payload.get("capabilities", [])
    if isinstance(capabilities, str):
        capabilities = [capabilities]
    if not isinstance(capabilities, list) or not all(isinstance(item, str) for item in capabilities):
        raise ValueError("profile capabilities must be a string list")
    personality = payload.get("personality", {})
    if not isinstance(personality, (dict, str)):
        raise ValueError("profile personality must be a mapping or string")
    limits = payload.get("limits", {})
    if not isinstance(limits, dict):
        raise ValueError("profile limits must be a mapping")
    return RobotProfile(
        name=str(payload.get("name", "Sesame Robot")),
        capabilities=tuple(capabilities),
        personality=personality,
        limits=limits,
    )


def get_capability(name: str, path: str | Path | None = None) -> bool:
    return load_profile(path).get_capability(name)


def get_personality(key: str | None = None, path: str | Path | None = None) -> Any:
    return load_profile(path).get_personality(key)


def _reject_forbidden_profile_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in FORBIDDEN_PROFILE_KEYS:
                raise ValueError(f"profile field cannot override safety boundary: {key}")
            _reject_forbidden_profile_fields(child)
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden_profile_fields(child)


def _parse_limited_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    current_key: str | None = None
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].rstrip()
        if not line:
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if "\t" in raw_line:
            raise ValueError(f"invalid yaml tab indentation at line {line_number}")
        if indent == 0:
            if ":" not in stripped or stripped.startswith("-"):
                raise ValueError(f"invalid yaml mapping at line {line_number}")
            key, value = stripped.split(":", 1)
            key = key.strip()
            if not key:
                raise ValueError(f"empty yaml key at line {line_number}")
            value = value.strip()
            root[key] = {} if value == "" else _parse_scalar(value)
            current_key = key if value == "" else None
            continue
        if indent != 2 or current_key is None:
            raise ValueError(f"unsupported yaml structure at line {line_number}")
        if stripped.startswith("- "):
            existing = root.get(current_key)
            if existing == {}:
                existing = []
                root[current_key] = existing
            if not isinstance(existing, list):
                raise ValueError(f"mixed yaml collection at line {line_number}")
            existing.append(_parse_scalar(stripped[2:].strip()))
            continue
        if ":" not in stripped:
            raise ValueError(f"invalid yaml nested mapping at line {line_number}")
        existing = root.get(current_key)
        if not isinstance(existing, dict):
            raise ValueError(f"mixed yaml collection at line {line_number}")
        key, value = stripped.split(":", 1)
        if not key.strip():
            raise ValueError(f"empty yaml key at line {line_number}")
        existing[key.strip()] = _parse_scalar(value.strip())
    return root


def _parse_scalar(value: str) -> Any:
    if value == "":
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value
