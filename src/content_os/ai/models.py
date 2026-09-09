"""Validated request/response contracts for AI providers."""

from typing import Any

from pydantic import BaseModel, Field


class AIRequest(BaseModel):
    """Provider-neutral input for one bounded model invocation."""

    task: str = Field(min_length=1)
    system_prompt: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)
    response_schema: dict[str, Any] | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class AIResponse(BaseModel):
    """Provider-neutral validated output for one model invocation."""

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    content: str = Field(min_length=1)
    structured_output: dict[str, Any] | None = None
    request_id: str = Field(min_length=1)
    attempt: int = Field(ge=1)
