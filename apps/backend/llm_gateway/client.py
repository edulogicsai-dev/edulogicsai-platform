"""
Thin async client for the LiteLLM proxy. Per CLAUDE.md: "All LLM calls route
through LiteLLM -- never direct Anthropic SDK." This is the only place
apps/backend is allowed to reach an LLM from.

Not exercised against a live proxy/key in changes/2026/07/17/nexus-orchestration/
(see that epic's SPEC.md Requirements Discovery) -- verified via httpx.MockTransport.
"""

from typing import Optional

import httpx


class LiteLLMGatewayClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None) -> None:
        self._base_url = base_url
        self._api_key = api_key

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(base_url=self._base_url) as client:
                resp = await client.get("/health")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def complete(self, model: str, messages: list[dict]) -> dict:
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.post(
                "/chat/completions",
                json={"model": model, "messages": messages},
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()
