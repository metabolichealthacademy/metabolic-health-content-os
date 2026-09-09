"""Bounded gateway for provider-independent AI calls."""

from content_os.ai.models import AIRequest, AIResponse
from content_os.ai.provider import AIProvider, AIProviderError


class AIGateway:
    """Execute provider calls behind a stable interface with bounded retries."""

    def __init__(self, provider: AIProvider, *, max_attempts: int = 2) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.provider = provider
        self.max_attempts = max_attempts

    def generate(self, request: AIRequest) -> AIResponse:
        last_error: AIProviderError | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.provider.generate(request, attempt=attempt)
                return AIResponse.model_validate(response)
            except AIProviderError as exc:
                last_error = exc

        raise AIProviderError(
            f"Provider {self.provider.name} failed after {self.max_attempts} attempts"
        ) from last_error
