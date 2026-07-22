from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AssistantAction(str, Enum):
    SAY = "say"
    SET_FACE = "set_face"
    ROBOT_COMMAND = "robot_command"
    DENY = "deny"


@dataclass(frozen=True)
class AssistantRequest:
    text: str
    wake_word_detected: bool = True


@dataclass(frozen=True)
class AssistantStep:
    action: AssistantAction
    value: str
    reason: str


@dataclass(frozen=True)
class AssistantPlan:
    transcript: str
    steps: tuple[AssistantStep, ...]


@dataclass(frozen=True)
class AssistantPolicy:
    allow_motion_commands: bool = False
    allow_expressive_commands: bool = True


class MockWakeWord:
    def __init__(self, wake_word: str = "sesame"):
        self.wake_word = wake_word.lower()

    def detect(self, text: str) -> bool:
        return self.wake_word in text.lower()


class MockSpeechRecognizer:
    def transcribe(self, text_input: str) -> str:
        return text_input.strip()


class MockLanguageModel:
    def plan(self, transcript: str) -> tuple[AssistantStep, ...]:
        normalized = transcript.lower()
        if "reset emergency stop" in normalized or "解除急停" in transcript:
            return (
                AssistantStep(AssistantAction.ROBOT_COMMAND, "reset_emergency_stop", "user requested emergency stop reset"),
                AssistantStep(AssistantAction.SAY, "Emergency stop reset needs confirmation.", "explain confirmation"),
            )
        if "emergency" in normalized or "急停" in transcript:
            return (
                AssistantStep(AssistantAction.ROBOT_COMMAND, "emergency_stop", "user requested emergency stop"),
                AssistantStep(AssistantAction.SAY, "Emergency stop is active.", "confirm emergency stop"),
            )
        if "happy" in normalized or "开心" in transcript:
            return (
                AssistantStep(AssistantAction.SET_FACE, "happy", "user requested expression"),
                AssistantStep(AssistantAction.SAY, "I changed the face to happy.", "confirm expression"),
            )
        if "wave" in normalized or "挥手" in transcript:
            return (
                AssistantStep(AssistantAction.ROBOT_COMMAND, "wave", "user requested expressive action"),
                AssistantStep(AssistantAction.SAY, "I can wave.", "confirm action"),
            )
        if "follow" in normalized or "跟随" in transcript:
            return (
                AssistantStep(AssistantAction.ROBOT_COMMAND, "walk_forward", "user requested movement"),
                AssistantStep(AssistantAction.SAY, "Following needs the safety layer enabled.", "explain restriction"),
            )
        return (AssistantStep(AssistantAction.SAY, "I heard you.", "default response"),)


class MockTextToSpeech:
    def synthesize(self, text: str) -> bytes:
        return text.encode("utf-8")


class AssistantCommandPolicy:
    EXPRESSIVE_COMMANDS = {"wave"}
    ALWAYS_ALLOWED_COMMANDS = {"stop", "emergency_stop", "reset_emergency_stop"}
    MOTION_COMMANDS = {"walk_forward", "walk_backward", "turn_left", "turn_right"}

    def __init__(self, policy: AssistantPolicy):
        self.policy = policy

    def filter_step(self, step: AssistantStep) -> AssistantStep:
        if step.action != AssistantAction.ROBOT_COMMAND:
            return step
        command = step.value
        if command in self.ALWAYS_ALLOWED_COMMANDS:
            return step
        if command in self.EXPRESSIVE_COMMANDS and self.policy.allow_expressive_commands:
            return step
        if command in self.MOTION_COMMANDS and self.policy.allow_motion_commands:
            return step
        return AssistantStep(AssistantAction.DENY, command, "command is blocked by local assistant policy")


class MockAssistantPipeline:
    def __init__(
        self,
        wake_word: MockWakeWord | None = None,
        recognizer: MockSpeechRecognizer | None = None,
        language_model: MockLanguageModel | None = None,
        text_to_speech: MockTextToSpeech | None = None,
        policy: AssistantPolicy | None = None,
    ):
        self.wake_word = wake_word or MockWakeWord()
        self.recognizer = recognizer or MockSpeechRecognizer()
        self.language_model = language_model or MockLanguageModel()
        self.text_to_speech = text_to_speech or MockTextToSpeech()
        self.command_policy = AssistantCommandPolicy(policy or AssistantPolicy())

    def handle_text(self, text_input: str) -> AssistantPlan:
        if not self.wake_word.detect(text_input):
            return AssistantPlan(transcript="", steps=())

        transcript = self.recognizer.transcribe(text_input)
        planned_steps = self.language_model.plan(transcript)
        filtered_steps = tuple(self.command_policy.filter_step(step) for step in planned_steps)
        for step in filtered_steps:
            if step.action == AssistantAction.SAY:
                self.text_to_speech.synthesize(step.value)
        return AssistantPlan(transcript=transcript, steps=filtered_steps)


def plan_to_jsonable(plan: AssistantPlan) -> dict[str, object]:
    return {
        "transcript": plan.transcript,
        "steps": [
            {
                "action": step.action.value,
                "value": step.value,
                "reason": step.reason,
            }
            for step in plan.steps
        ],
    }
