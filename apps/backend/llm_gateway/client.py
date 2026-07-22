"""
Thin async client for the LiteLLM proxy. Per CLAUDE.md: "All LLM calls route
through LiteLLM -- never direct Anthropic SDK." This is the only place
apps/backend is allowed to reach an LLM from.

Wired to real Anthropic-backed LLM calls (ARIA/MIRA/QUINN) as of the
web-chat-integration follow-on work -- default_gateway_client() below reads
the live proxy's location from the environment. Still verified in this
repo's own test suite via httpx.MockTransport / fake gateway objects, not a
live proxy -- no LiteLLM proxy or Anthropic key is available in this
development environment (same constraint as changes/2026/07/17/
nexus-orchestration/SPEC.md Requirements Discovery).
"""

import os
from typing import Optional

import httpx


class LiteLLMGatewayClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None) -> None:
        self._base_url = base_url
        self._api_key = api_key

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=60.0) as client:
                resp = await client.get("/health")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def complete(self, model: str, messages: list[dict]) -> dict:
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        async with httpx.AsyncClient(base_url=self._base_url, timeout=60.0) as client:
            resp = await client.post(
                "/chat/completions",
                json={"model": model, "messages": messages},
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()


def default_gateway_client() -> LiteLLMGatewayClient:
    """
    Constructs the process-wide gateway client from the environment --
    LITELLM_BASE_URL (the running `litellm --config config/litellm.yaml`
    proxy's address, default matching litellm's own default port) and
    LITELLM_MASTER_KEY (config/litellm.yaml's general_settings.master_key).
    Called once at import time by domains/mcat/domain_config.py; safe to
    call with no env vars set (construction never makes a network call --
    see LiteLLMGatewayClient.__init__) so importing the module never fails
    even where no real proxy exists yet, per CLAUDE.md's per-package
    isolation and this repo's tests.
    """
    return LiteLLMGatewayClient(
        base_url=os.environ.get("LITELLM_BASE_URL", "http://localhost:4000"),
        api_key=os.environ.get("LITELLM_MASTER_KEY"),
    )
