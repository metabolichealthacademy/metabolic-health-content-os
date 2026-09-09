"""Deterministic mock AI provider used for Task 4 verification."""

from uuid import uuid4
from collections.abc import Callable

from content_os.ai.models import AIRequest, AIResponse
from content_os.ai.provider import AIProvider, AIProviderError


MockBehavior = Callable[[AIRequest, int], AIResponse]


class MockAIProvider(AIProvider):
    """Configurable deterministic provider with no external model connection."""

    name = "mock"

    def __init__(
        self,
        *,
        model: str = "mock-v1",
        behavior: MockBehavior | None = None,
        fail_attempts: int = 0,
    ) -> None:
        self.model = model
        self.behavior = behavior
        self.fail_attempts = fail_attempts

    def generate(self, request: AIRequest, *, attempt: int = 1) -> AIResponse:
        if attempt <= self.fail_attempts:
            raise AIProviderError(f"Mock provider failure on attempt {attempt}")

        if self.behavior is not None:
            return self.behavior(request, attempt)

        return AIResponse(
            provider=self.name,
            model=self.model,
            content=f"MOCK RESPONSE: {request.task}",
            structured_output=None,
            request_id=f"mock-{uuid4()}",
            attempt=attempt,
        )
