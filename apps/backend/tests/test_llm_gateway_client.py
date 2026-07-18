import httpx
import pytest

from llm_gateway.client import LiteLLMGatewayClient


def _patch_transport(monkeypatch, handler) -> None:
    """Route every httpx.AsyncClient this test creates through a mock transport."""
    transport = httpx.MockTransport(handler)
    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)


@pytest.mark.asyncio
async def test_health_returns_true_on_200(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        return httpx.Response(200, json={"status": "healthy"})

    _patch_transport(monkeypatch, handler)

    client = LiteLLMGatewayClient(base_url="http://litellm-proxy.test")
    assert await client.health() is True


@pytest.mark.asyncio
async def test_health_returns_false_on_connection_error(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    _patch_transport(monkeypatch, handler)

    client = LiteLLMGatewayClient(base_url="http://litellm-proxy.test")
    assert await client.health() is False


@pytest.mark.asyncio
async def test_complete_returns_parsed_json(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/chat/completions"
        return httpx.Response(200, json={"choices": [{"message": {"content": "aria"}}]})

    _patch_transport(monkeypatch, handler)

    client = LiteLLMGatewayClient(base_url="http://litellm-proxy.test", api_key="test-key")
    result = await client.complete(model="haiku-intent", messages=[{"role": "user", "content": "hi"}])
    assert result["choices"][0]["message"]["content"] == "aria"
