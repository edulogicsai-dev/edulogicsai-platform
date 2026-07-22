"""
MIRA -- the Motivation & Resilience Coach for MCATai.
See changes/2026/07/15/mira-agent/SPEC.md (FR1-FR4) and
domains/mcat/prompts/mira_v1.md for MIRA's authored system prompt.

respond() calls Claude (via LiteLLMGatewayClient, model alias "sonnet-tutor")
for the actual coaching content and for distress/recovery detection -- MIRA's
whole purpose is reading emotional state, so (per the same "use the LLM's
understanding, not keyword heuristics" requirement applied to ARIA)
recovery detection and the reported risk_level both come from the model's
own judgment now, not KeywordDistressEstimator/KeywordRecoverySignalClassifier
(removed -- see llm_support.py for the shared JSON-completion plumbing).
"""

from typing import AsyncIterator, List, Optional

from domains._contracts.agent_io import AgentInput, AgentOutput, EpisodicMemory
from domains._contracts.base_agent import BaseAgent
from domains.mcat.agents.llm_support import (
    complete_json,
    render_episodic_context,
    render_session_history,
    as_risk_level,
    as_str,
)
from llm_gateway.client import LiteLLMGatewayClient, default_gateway_client
from prompt_registry.client import FilePromptRegistryClient, PromptRegistryClient

MIRA_JSON_CONTRACT = """

## Required Response Format

Respond with ONLY a single JSON object -- no markdown code fences, no prose \
outside the JSON. Use exactly these keys:

{
  "response": "<your coaching message, per all the guidance above>",
  "recovered": true or false -- true only if the signals described in \
\"When to Hand Off > Back to ARIA\" are present in the student's recent messages,
  "risk_level": "low" | "medium" | "high" -- per \"When to Hand Off > Human \
escalation\", high means genuine distress requiring human escalation, not \
just normal academic frustration,
  "session_notes": "<brief internal note: emotional state observed, \
strategy offered, whether you see improvement -- stored for your next \
session with this student>"
}
"""


def _find_handoff_cause(episodic_context: List[EpisodicMemory], message: str) -> str:
    """Most recent episodic entry, as the frustration context ARIA recorded.
    Reuses the same channel ARIA established for its own cross-turn signal
    (see SPEC.md FR2) -- no dedicated 'handoff context' field exists yet."""
    if not episodic_context:
        return message
    most_recent = max(episodic_context, key=lambda mem: mem.occurredAt)
    return most_recent.summary


class Mira(BaseAgent):
    id = "mira"

    def __init__(
        self,
        prompt_client: Optional[PromptRegistryClient] = None,
        gateway_client: Optional[LiteLLMGatewayClient] = None,
    ) -> None:
        self._prompt_client = prompt_client or FilePromptRegistryClient(domain="mcat")
        self._gateway_client = gateway_client or default_gateway_client()

    async def fetch_prompt(self) -> str:
        return self._prompt_client.get_prompt("mira", "v1")

    async def respond(self, input: AgentInput) -> AsyncIterator[AgentOutput]:
        handoff_cause = _find_handoff_cause(input.episodic_context, input.message)

        system_prompt = await self.fetch_prompt() + MIRA_JSON_CONTRACT
        user_content = (
            f"Why MIRA was brought in (what ARIA or the student's own message flagged): {handoff_cause}\n\n"
            f"Student's message: {input.message}\n\n"
            f"Episodic context (this student's history):\n{render_episodic_context(input.episodic_context)}\n\n"
            f"Recent conversation this session:\n{render_session_history(input.session_history, limit=4)}"
        )

        parsed = await complete_json(self._gateway_client, system_prompt, user_content)

        risk_level = as_risk_level(parsed.get("risk_level"))
        recovered = bool(parsed.get("recovered")) if risk_level != "high" else False

        # Safety takes priority over a simultaneous recovery signal -- even
        # if the model reports both, high distress wins.
        suggested_handoff: Optional[str] = "aria" if recovered else None

        yield AgentOutput(
            response=as_str(parsed.get("response")),
            agent_id=self.id,
            cited_chunks=[],
            suggested_handoff=suggested_handoff,
            mastery_update=None,
            session_notes=as_str(parsed.get("session_notes")),
            risk_level=risk_level,
        )

    async def write_episodic_memory(self, input: AgentInput, output: AgentOutput) -> None:
        # No persistence layer exists yet (paused core-data-schema epic).
        # Placeholder no-op -- see SPEC.md Out of Scope.
        return None
