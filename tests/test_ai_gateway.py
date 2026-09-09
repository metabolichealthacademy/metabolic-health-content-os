import pytest
from pydantic import ValidationError

from content_os.ai import AIGateway, AIProviderError, AIRequest, AIResponse, MockAIProvider


def request() -> AIRequest:
    return AIRequest(
        task="draft educational summary",
        system_prompt="Return bounded educational content.",
        user_prompt="Explain insulin resistance.",
        metadata={"workflow_id": "wf-test"},
    )


def test_mock_provider_returns_provider_neutral_response() -> None:
    response = AIGateway(MockAIProvider()).generate(request())

    assert response.provider == "mock"
    assert response.model == "mock-v1"
    assert response.content == "MOCK RESPONSE: draft educational summary"
    assert response.attempt == 1
    assert response.request_id.startswith("mock-")


def test_gateway_retries_transient_provider_error() -> None:
    response = AIGateway(MockAIProvider(fail_attempts=1), max_attempts=2).generate(request())

    assert response.attempt == 2


def test_gateway_stops_after_bounded_attempts() -> None:
    gateway = AIGateway(MockAIProvider(fail_attempts=3), max_attempts=2)

    with pytest.raises(AIProviderError, match="failed after 2 attempts"):
        gateway.generate(request())


def test_gateway_rejects_invalid_retry_configuration() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        AIGateway(MockAIProvider(), max_attempts=0)


def test_request_contract_rejects_empty_prompts() -> None:
    with pytest.raises(ValidationError):
        AIRequest(task="", system_prompt="", user_prompt="")


def test_custom_mock_behavior_is_validated() -> None:
    def behavior(ai_request: AIRequest, attempt: int) -> AIResponse:
        return AIResponse(
            provider="mock",
            model="structured-mock",
            content="validated structured response",
            structured_output={"task": ai_request.task},
            request_id="mock-structured-1",
            attempt=attempt,
        )

    response = AIGateway(MockAIProvider(behavior=behavior)).generate(request())

    assert response.structured_output == {"task": "draft educational summary"}
