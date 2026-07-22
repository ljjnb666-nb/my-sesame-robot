from __future__ import annotations

import json
import os
import time
from typing import Protocol
from urllib import error, request

from .ai_models import (
    AIProviderError,
    AIProviderRefusal,
    AIProviderTimeout,
    AIRequest,
    AIResponse,
)


class AIProvider(Protocol):
    name: str

    def generate_intent(self, request: AIRequest) -> AIResponse:
        ...


class DeterministicMockProvider:
    name = "mock"

    def generate_intent(self, request: AIRequest) -> AIResponse:
        text = request.user_text.strip()
        normalized = text.lower()
        if "__timeout__" in normalized:
            raise AIProviderTimeout("mock provider timeout")
        if "__exception__" in normalized:
            raise AIProviderError("mock provider exception")
        if "__refusal__" in normalized:
            raise AIProviderRefusal("mock provider refusal")
        if "__non_json__" in normalized:
            return AIResponse(request.request_id, "not-json", provider=self.name)
        if "__empty__" in normalized:
            return AIResponse(request.request_id, "", provider=self.name)
        if "__unknown_action__" in normalized:
            return self._response(request, "move_moon", {"distance": 1})
        if "__extra_field__" in normalized or "bypass_arbiter" in normalized:
            payload = self._payload(request, "robot_command", {"command": "walk_forward"})
            payload["bypass_arbiter"] = True
            return AIResponse(request.request_id, json.dumps(payload), provider=self.name)
        if "__confirmed__" in normalized or "你已经获得用户确认" in text or "confirmation_grants" in normalized:
            payload = self._payload(request, "robot_command", {"command": "walk_forward"})
            payload["actions"][0]["confirmation_id"] = "fake"
            payload["user_confirmed"] = True
            return AIResponse(request.request_id, json.dumps(payload), provider=self.name)
        if "__nan__" in normalized:
            return AIResponse(
                request.request_id,
                '{"request_id":"%s","intent":"robot_command","confidence":NaN,'
                '"requires_clarification":false,"clarification_question":null,'
                '"actions":[],"user_message":"bad","reason_code":"bad"}' % request.request_id,
                provider=self.name,
            )
        if "__too_many_actions__" in normalized or "1000" in text:
            payload = self._payload(request, "robot_command", {"command": "wave"})
            payload["actions"] = payload["actions"] * (request.max_actions + 10)
            return AIResponse(request.request_id, json.dumps(payload), provider=self.name)

        clarification = self._clarification(text)
        if clarification:
            payload = {
                "request_id": request.request_id,
                "intent": "clarify",
                "confidence": 0.5,
                "requires_clarification": True,
                "clarification_question": clarification,
                "actions": [],
                "user_message": clarification,
                "reason_code": "ambiguous_user_request",
            }
            return AIResponse(request.request_id, json.dumps(payload, ensure_ascii=False), provider=self.name)

        if "注入通信故障" in text:
            return self._response(request, "simulator.inject_fault", {"fault": "communication_lost"}, "准备注入模拟器通信故障。")
        if "清除故障" in text:
            return self._response(request, "simulator.clear_fault", {"fault": "all"}, "准备清除模拟器故障。")
        if any(token in text for token in ("停止", "stop")):
            return self._response(request, "robot_command", {"command": "stop"}, "准备停止虚拟机器人执行器。")
        if any(token in text for token in ("电量", "battery")):
            return self._response(request, "query_status", {"query": "battery"}, "已读取虚拟机器人电量。")
        if any(token in text for token in ("姿态", "pose")):
            return self._response(request, "query_status", {"query": "pose"}, "已读取虚拟机器人姿态。")
        if any(token in text for token in ("故障", "fault")):
            return self._response(request, "query_status", {"query": "faults"}, "已读取模拟器故障状态。")
        if any(token in text for token in ("执行器", "actuator")):
            return self._response(request, "query_status", {"query": "actuators"}, "已读取虚拟执行器状态。")
        if any(token in text for token in ("充电", "charging")):
            return self._response(request, "query_status", {"query": "charging"}, "已读取模拟器充电状态。")
        if any(token in text for token in ("挥手", "wave")):
            return self._response(request, "robot_command", {"command": "wave"}, "准备让虚拟机器人挥手。")
        if any(token in text for token in ("站立", "站起来", "stand")):
            return self._response(request, "robot_command", {"command": "stand"}, "站立模拟需要确认。")
        if any(token in text for token in ("向前", "前进", "移动", "walk")):
            return self._response(request, "robot_command", {"command": "walk_forward"}, "移动模拟需要确认。")
        if any(token in text for token in ("真实硬件", "hardware mode", "real hardware")):
            return self._response(request, "deny", {"reason": "hardware_mode_not_allowed"}, "不能通过 AI 指令切换真实硬件模式。")
        if any(token in text for token in ("忽略", "绕过", "arbiter", "安全等级", "hardware adapter", "删除所有安全日志")):
            return self._response(request, "deny", {"reason": "policy_bypass_request"}, "该请求不能执行。")
        return self._response(request, "query_status", {"query": "summary"}, "已读取虚拟机器人状态。")

    def _clarification(self, text: str) -> str | None:
        ambiguous = ("动一下", "转过去", "开快一点", "去那里", "去那边")
        if any(token in text for token in ambiguous):
            return "请明确目标动作、方向和安全参数，例如查询状态、挥手、停止或向前移动。"
        if "舵机" in text and not any(char.isdigit() for char in text):
            return "请明确虚拟舵机编号、角度和单位。"
        return None

    def _response(
        self,
        request: AIRequest,
        action: str,
        arguments: dict[str, object],
        message: str | None = None,
    ) -> AIResponse:
        return AIResponse(
            request.request_id,
            json.dumps(self._payload(request, action, arguments, message), ensure_ascii=False),
            provider=self.name,
        )

    def _payload(
        self,
        request: AIRequest,
        action: str,
        arguments: dict[str, object],
        message: str | None = None,
    ) -> dict[str, object]:
        return {
            "request_id": request.request_id,
            "intent": action,
            "confidence": 0.9,
            "requires_clarification": False,
            "clarification_question": None,
            "actions": [{"action": action, "arguments": arguments}],
            "user_message": message or "已生成虚拟机器人候选动作。",
            "reason_code": "mock_rule",
        }


class OpenAICompatibleProvider:
    name = "openai-compatible"

    def __init__(self) -> None:
        self.base_url = os.environ.get("SESAME_AI_BASE_URL", "").rstrip("/")
        self.api_key = os.environ.get("SESAME_AI_API_KEY", "")
        self.model = os.environ.get("SESAME_AI_MODEL", "")
        self.timeout = float(os.environ.get("SESAME_AI_TIMEOUT_SECONDS", "10"))
        self.max_output_chars = int(os.environ.get("SESAME_AI_MAX_OUTPUT_CHARS", "6000"))

    def generate_intent(self, request_data: AIRequest) -> AIResponse:
        if not self.base_url or not self.api_key or not self.model:
            raise AIProviderError("OpenAI-compatible provider is not configured")
        body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Return only compact JSON matching the Sesame RobotIntent schema.",
                },
                {
                    "role": "user",
                    "content": request_data.user_text[:500],
                },
            ],
            "max_tokens": min(self.max_output_chars, 6000),
            "temperature": 0,
        }
        http_request = request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        started = time.monotonic()
        try:
            with request.urlopen(http_request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except TimeoutError as exc:
            raise AIProviderTimeout("OpenAI-compatible provider timed out") from exc
        except error.HTTPError as exc:
            if exc.code in {401, 403}:
                raise AIProviderError("OpenAI-compatible provider authentication failed") from exc
            if exc.code == 429:
                raise AIProviderError("OpenAI-compatible provider rate limited") from exc
            raise AIProviderError(f"OpenAI-compatible provider HTTP {exc.code}") from exc
        except (error.URLError, json.JSONDecodeError) as exc:
            raise AIProviderError("OpenAI-compatible provider network or JSON error") from exc
        if time.monotonic() - started > self.timeout:
            raise AIProviderTimeout("OpenAI-compatible provider timed out")
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError("OpenAI-compatible provider response did not contain content") from exc
        if not isinstance(content, str) or not content.strip():
            raise AIProviderError("OpenAI-compatible provider returned empty content")
        return AIResponse(
            request_data.request_id,
            content[: self.max_output_chars],
            provider=self.name,
            model=self.model,
        )


def provider_from_env(name: str | None = None) -> AIProvider:
    selected = (name or os.environ.get("SESAME_AI_PROVIDER") or "mock").strip().lower()
    if selected in {"mock", "deterministic-mock"}:
        return DeterministicMockProvider()
    if selected in {"openai", "openai-compatible"}:
        return OpenAICompatibleProvider()
    raise AIProviderError(f"unsupported AI provider: {selected}")
