from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .security import (
    CHAT_TEXT_LIMIT,
    FORBIDDEN_REQUEST_FIELDS,
    MAX_CONFIRMATION_ID_CHARS,
    MAX_FAULT_CHARS,
)


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_fields(cls, value: Any) -> Any:
        if isinstance(value, dict):
            forbidden = set(value) & FORBIDDEN_REQUEST_FIELDS
            if forbidden:
                raise ValueError("request contains forbidden authority fields")
        return value


class ChatRequest(StrictBaseModel):
    text: str = Field(min_length=1, max_length=CHAT_TEXT_LIMIT)
    confirmationId: str | None = Field(default=None, max_length=MAX_CONFIRMATION_ID_CHARS)

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value

    @field_validator("confirmationId")
    @classmethod
    def confirmation_id_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("confirmationId must not be blank")
        return value


class FaultRequest(StrictBaseModel):
    fault: str = Field(min_length=1, max_length=MAX_FAULT_CHARS)

    @field_validator("fault")
    @classmethod
    def fault_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("fault must not be blank")
        return value


class HealthResponse(BaseModel):
    status: str
    version: str
    runtimeMode: str
    simulatorOnly: bool
    provider: str
