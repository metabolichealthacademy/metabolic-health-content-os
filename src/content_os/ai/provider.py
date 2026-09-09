"""Abstract provider contract and normalized provider errors."""

from abc import ABC, abstractmethod

from content_os.ai.models import AIRequest, AIResponse


class AIProviderError(RuntimeError):
    """Normalized provider failure safe for orchestration-level handling."""


class AIProvider(ABC):
    """Provider-independent interface implemented by all model adapters."""

    name: str

    @abstractmethod
    def generate(self, request: AIRequest, *, attempt: int = 1) -> AIResponse:
        """Execute one bounded model request and return a validated response."""
