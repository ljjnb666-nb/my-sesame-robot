from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from .sanitizer import memory_key_allowed, sanitize_memory_value


DEFAULT_MEMORY_PATH = Path.home() / ".sesame_robot" / "memory.json"
MEMORY_VERSION = 1


def _default_data() -> dict[str, Any]:
    return {
        "version": MEMORY_VERSION,
        "short_term": {
            "conversation_context": [],
            "task_context": {},
        },
        "long_term": {
            "user_preferences": {},
            "robot_config": {},
        },
    }


@dataclass
class ShortTermMemory:
    conversation_context: list[dict[str, Any]] = field(default_factory=list)
    task_context: dict[str, Any] = field(default_factory=dict)
    max_turns: int = 20

    def store(self, key: str, value: Any) -> None:
        if not memory_key_allowed(key):
            return
        cleaned = sanitize_memory_value(value)
        if key == "conversation_context":
            if isinstance(cleaned, list):
                self.conversation_context = [dict(item) for item in cleaned if isinstance(item, dict)][-self.max_turns :]
            elif isinstance(cleaned, dict):
                self.conversation_context.append(cleaned)
                self.conversation_context = self.conversation_context[-self.max_turns :]
            else:
                self.conversation_context.append({"entry": cleaned})
                self.conversation_context = self.conversation_context[-self.max_turns :]
            return
        if key == "task_context" and isinstance(cleaned, dict):
            self.task_context = cleaned
            return
        self.task_context[key] = cleaned

    def retrieve(self, key: str | None = None) -> Any:
        if key is None:
            return {
                "conversation_context": deepcopy(self.conversation_context),
                "task_context": deepcopy(self.task_context),
            }
        if key == "conversation_context":
            return deepcopy(self.conversation_context)
        if key == "task_context":
            return deepcopy(self.task_context)
        return deepcopy(self.task_context.get(key))

    def update(self, key: str, value: Any) -> None:
        if key == "task_context" and isinstance(value, dict):
            current = dict(self.task_context)
            current.update(sanitize_memory_value(value))
            self.task_context = current
            return
        self.store(key, value)

    def clear(self, key: str | None = None) -> None:
        if key is None:
            self.conversation_context.clear()
            self.task_context.clear()
        elif key == "conversation_context":
            self.conversation_context.clear()
        elif key == "task_context":
            self.task_context.clear()
        else:
            self.task_context.pop(key, None)

    def to_json(self) -> dict[str, Any]:
        return {
            "conversation_context": deepcopy(self.conversation_context),
            "task_context": deepcopy(self.task_context),
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "ShortTermMemory":
        memory = cls()
        conversation = payload.get("conversation_context", [])
        tasks = payload.get("task_context", {})
        if isinstance(conversation, list):
            memory.conversation_context = sanitize_memory_value(conversation)[-memory.max_turns :]
        if isinstance(tasks, dict):
            memory.task_context = sanitize_memory_value(tasks)
        return memory


@dataclass
class LongTermMemory:
    user_preferences: dict[str, Any] = field(default_factory=dict)
    robot_config: dict[str, Any] = field(default_factory=dict)

    def store(self, key: str, value: Any) -> None:
        if not memory_key_allowed(key):
            return
        cleaned = sanitize_memory_value(value)
        if key == "user_preferences" and isinstance(cleaned, dict):
            self.user_preferences = cleaned
            return
        if key == "robot_config" and isinstance(cleaned, dict):
            self.robot_config = cleaned
            return
        self.user_preferences[key] = cleaned

    def retrieve(self, key: str | None = None) -> Any:
        if key is None:
            return {
                "user_preferences": deepcopy(self.user_preferences),
                "robot_config": deepcopy(self.robot_config),
            }
        if key == "user_preferences":
            return deepcopy(self.user_preferences)
        if key == "robot_config":
            return deepcopy(self.robot_config)
        if key in self.user_preferences:
            return deepcopy(self.user_preferences[key])
        return deepcopy(self.robot_config.get(key))

    def update(self, key: str, value: Any) -> None:
        cleaned = sanitize_memory_value(value)
        if key == "user_preferences" and isinstance(cleaned, dict):
            current = dict(self.user_preferences)
            current.update(cleaned)
            self.user_preferences = current
            return
        if key == "robot_config" and isinstance(cleaned, dict):
            current = dict(self.robot_config)
            current.update(cleaned)
            self.robot_config = current
            return
        self.store(key, cleaned)

    def clear(self, key: str | None = None) -> None:
        if key is None:
            self.user_preferences.clear()
            self.robot_config.clear()
        elif key == "user_preferences":
            self.user_preferences.clear()
        elif key == "robot_config":
            self.robot_config.clear()
        else:
            self.user_preferences.pop(key, None)
            self.robot_config.pop(key, None)

    def to_json(self) -> dict[str, Any]:
        return {
            "user_preferences": deepcopy(self.user_preferences),
            "robot_config": deepcopy(self.robot_config),
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "LongTermMemory":
        memory = cls()
        preferences = payload.get("user_preferences", {})
        config = payload.get("robot_config", {})
        if isinstance(preferences, dict):
            memory.user_preferences = sanitize_memory_value(preferences)
        if isinstance(config, dict):
            memory.robot_config = sanitize_memory_value(config)
        return memory


class MemoryManager:
    def __init__(
        self,
        storage_path: str | os.PathLike[str] | None = None,
        *,
        short_term: ShortTermMemory | None = None,
        long_term: LongTermMemory | None = None,
    ) -> None:
        self.storage_path = Path(storage_path) if storage_path is not None else DEFAULT_MEMORY_PATH
        self.short_term = short_term or ShortTermMemory()
        self.long_term = long_term or LongTermMemory()
        self.last_persistence_error: str | None = None
        self.last_load_error: str | None = None
        self.quarantined_path: Path | None = None
        self._load()

    def store(self, scope: str, key: str, value: Any) -> None:
        self._memory(scope).store(key, value)
        self._save()

    def retrieve(self, scope: str, key: str | None = None) -> Any:
        return self._memory(scope).retrieve(key)

    def update(self, scope: str, key: str, value: Any) -> None:
        self._memory(scope).update(key, value)
        self._save()

    def clear(self, scope: str | None = None, key: str | None = None) -> None:
        if scope is None:
            self.short_term.clear()
            self.long_term.clear()
        else:
            self._memory(scope).clear(key)
        self._save()

    def record_conversation_turn(self, request_id: str, user_text: str, robot_reply: str, result_code: str) -> None:
        self.short_term.store("conversation_context", {
            "request_id": request_id,
            "user": user_text,
            "reply": robot_reply,
            "result_code": result_code,
        })
        self._save()

    def _memory(self, scope: str) -> ShortTermMemory | LongTermMemory:
        if scope == "short_term":
            return self.short_term
        if scope == "long_term":
            return self.long_term
        raise ValueError("memory scope must be short_term or long_term")

    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
            self._validate_loaded_payload(payload)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            self._quarantine_corrupt_file(exc)
            self.short_term = ShortTermMemory()
            self.long_term = LongTermMemory()
            return
        self.short_term = ShortTermMemory.from_json(payload["short_term"])
        self.long_term = LongTermMemory.from_json(payload["long_term"])

    def _validate_loaded_payload(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            raise ValueError("memory file root must be an object")
        if payload.get("version") != MEMORY_VERSION:
            raise ValueError("memory file version is incompatible")
        if not isinstance(payload.get("short_term"), dict):
            raise ValueError("memory short_term section must be an object")
        if not isinstance(payload.get("long_term"), dict):
            raise ValueError("memory long_term section must be an object")
        short_term = payload["short_term"]
        long_term = payload["long_term"]
        if not isinstance(short_term.get("conversation_context", []), list):
            raise ValueError("memory conversation_context must be a list")
        if not isinstance(short_term.get("task_context", {}), dict):
            raise ValueError("memory task_context must be an object")
        if not isinstance(long_term.get("user_preferences", {}), dict):
            raise ValueError("memory user_preferences must be an object")
        if not isinstance(long_term.get("robot_config", {}), dict):
            raise ValueError("memory robot_config must be an object")

    def _quarantine_corrupt_file(self, exc: Exception) -> None:
        self.last_load_error = str(exc)
        target = self._corrupt_path()
        try:
            self.storage_path.replace(target)
            self.quarantined_path = target
        except OSError as rename_exc:
            self.last_persistence_error = str(rename_exc)

    def _corrupt_path(self) -> Path:
        base = self.storage_path.with_name(f"{self.storage_path.name}.corrupt")
        if not base.exists():
            return base
        for index in range(1, 1000):
            candidate = self.storage_path.with_name(f"{self.storage_path.name}.corrupt.{index}")
            if not candidate.exists():
                return candidate
        return self.storage_path.with_name(f"{self.storage_path.name}.corrupt.latest")

    def _save(self) -> None:
        payload = {
            "version": MEMORY_VERSION,
            "short_term": self.short_term.to_json(),
            "long_term": self.long_term.to_json(),
        }
        tmp_path: Path | None = None
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=self.storage_path.parent, suffix=".tmp") as tmp:
                json.dump(payload, tmp, ensure_ascii=False, indent=2, sort_keys=True)
                tmp_path = Path(tmp.name)
            tmp_path.replace(self.storage_path)
            self.last_persistence_error = None
        except OSError as exc:
            self.last_persistence_error = str(exc)
            if tmp_path is not None:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass
