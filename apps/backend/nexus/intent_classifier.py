"""
Entry-point intent classification: given a fresh session's first message,
decide which agent in the domain's roster should handle it. See
changes/2026/07/17/nexus-orchestration/changes/nexus-supervisor/SPEC.md FR4.
"""

from typing import Protocol

from llm_gateway.client import LiteLLMGatewayClient


class IntentClassifier(Protocol):
    async def classify(self, message: str, agent_ids: list[str]) -> str: ...


class KeywordIntentClassifier:
    """Test double / default until a live LLM key exists. Returns the first
    agent id in the roster -- see SPEC.md Gaps & Assumptions for why this is
    a reasonable default given how the current domain's roster is designed."""

    async def classify(self, message: str, agent_ids: list[str]) -> str:
        if not agent_ids:
            raise ValueError("agent_ids must not be empty")
        return agent_ids[0]


class LiteLLMIntentClassifier:
    """Real implementation -- calls the haiku-intent model via the LiteLLM
    gateway. Not exercised against a live key in this change (see epic
    SPEC.md Requirements Discovery); unit-tested against a mocked client."""

    def __init__(self, gateway_client: LiteLLMGatewayClient) -> None:
        self._gateway_client = gateway_client

    async def classify(self, message: str, agent_ids: list[str]) -> str:
        if not agent_ids:
            raise ValueError("agent_ids must not be empty")
        response = await self._gateway_client.complete(
            model="haiku-intent",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Classify the student's message into exactly one of these "
                        f"agent ids: {', '.join(agent_ids)}. Respond with only the id."
                    ),
                },
                {"role": "user", "content": message},
            ],
        )
        content = response["choices"][0]["message"]["content"].strip().lower()
        return content if content in agent_ids else agent_ids[0]
