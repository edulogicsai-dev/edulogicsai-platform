import pytest

from nexus.intent_classifier import KeywordIntentClassifier, LiteLLMIntentClassifier


@pytest.mark.asyncio
async def test_keyword_classifier_returns_first_agent() -> None:
    # AC4
    classifier = KeywordIntentClassifier()
    result = await classifier.classify("I'm frustrated", ["aria", "mira"])
    assert result == "aria"


class _FakeGatewayClient:
    def __init__(self, content: str) -> None:
        self._content = content

    async def complete(self, model: str, messages: list[dict]) -> dict:
        return {"choices": [{"message": {"content": self._content}}]}


@pytest.mark.asyncio
async def test_litellm_classifier_returns_models_choice() -> None:
    # AC5
    classifier = LiteLLMIntentClassifier(_FakeGatewayClient("mira"))
    result = await classifier.classify("I give up", ["aria", "mira", "quinn"])
    assert result == "mira"


@pytest.mark.asyncio
async def test_litellm_classifier_falls_back_on_invalid_response() -> None:
    # AC5
    classifier = LiteLLMIntentClassifier(_FakeGatewayClient("not-a-real-agent"))
    result = await classifier.classify("hello", ["aria", "mira", "quinn"])
    assert result == "aria"
