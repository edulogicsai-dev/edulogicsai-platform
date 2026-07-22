"""
ARIA -- the primary adaptive Socratic tutor for MCATai.
See changes/2026/07/10/aria-agent/SPEC.md (FR3-FR5) and
domains/mcat/prompts/aria_v1.md for ARIA's authored system prompt.

respond() calls Claude (via LiteLLMGatewayClient, model alias "sonnet-tutor")
for the actual tutoring content and for frustration detection (req: "use the
LLM's understanding of the message, not just keyword heuristics") -- see
llm_support.py for the shared JSON-completion plumbing and ARIA_JSON_CONTRACT
below for the exact response shape the model is asked for.

What stays deterministic, and why: the medical-advice guard (a hard safety
boundary shouldn't depend on model compliance), whether this concept has
been diagnostically assessed yet (real cross-turn state from
episodic_context, not something a single message can convey), and the
consecutive-successful-turns streak that drives the QUINN handoff (same
reason -- TurnOutcomeClassifier is unchanged, matching the readiness
heuristic already established here; only frustration detection moved to
the LLM, per the explicit requirement).
"""

import re
from typing import AsyncIterator, Optional, Protocol

from domains._contracts.agent_io import AgentInput, AgentOutput, EpisodicMemory
from domains._contracts.base_agent import BaseAgent
from domains.mcat.agents.llm_support import (
    complete_json,
    render_chunks,
    render_episodic_context,
    render_session_history,
    valid_cited_chunks,
    as_bool,
    as_risk_level,
    as_str,
)
from llm_gateway.client import LiteLLMGatewayClient, default_gateway_client
from prompt_registry.client import FilePromptRegistryClient, PromptRegistryClient

MEDICAL_ADVICE_PATTERNS = [
    r"\bshould i (take|see a doctor)\b",
    r"\bdo i have\b",
    r"\bwhat medication\b",
    r"\bcan you diagnose\b",
    r"\bmy (symptom|diagnosis|prescription)\b",
]

SUCCESS_MARKERS = [
    "that makes sense",
    "i understand",
    "got it",
    "oh i see",
    "that helps",
]

SUCCESSFUL_TURNS_KEY = "consecutive_successful_turns"

ARIA_JSON_CONTRACT = """

## Required Response Format

Respond with ONLY a single JSON object -- no markdown code fences, no prose \
outside the JSON. Use exactly these keys:

{
  "response": "<your tutoring message to the student, per all the guidance above>",
  "cited_chunks": ["<chunk_id>", "..."],
  "frustration_detected": true or false -- true only if the signals \
described in \"When to Hand Off > Hand off to MIRA\" are present in the \
student's recent messages,
  "risk_level": "low" | "medium" | "high"
}
"""


class TurnOutcomeClassifier(Protocol):
    def was_successful(self, input: AgentInput) -> bool: ...


class KeywordTurnOutcomeClassifier:
    """Interim heuristic -- see SPEC.md FR4. Replace with a real mastery signal later."""

    def was_successful(self, input: AgentInput) -> bool:
        lowered = input.message.lower()
        return any(marker in lowered for marker in SUCCESS_MARKERS)


def _is_medical_advice_request(message: str) -> bool:
    lowered = message.lower()
    return any(re.search(pattern, lowered) for pattern in MEDICAL_ADVICE_PATTERNS)


def _infer_concept_key(input: AgentInput) -> str:
    """Best-effort concept identifier. Heuristic -- see SPEC.md Gaps & Assumptions."""
    if input.retrieved_chunks:
        return input.retrieved_chunks[0].sourceId.lower()
    return input.message.strip().lower()[:64]


def _concept_previously_assessed(concept_key: str, episodic_context: list[EpisodicMemory]) -> bool:
    return any(concept_key in mem.summary.lower() for mem in episodic_context)


def _read_consecutive_successful_turns(episodic_context: list[EpisodicMemory]) -> int:
    for mem in sorted(episodic_context, key=lambda m: m.occurredAt, reverse=True):
        match = re.search(rf"{SUCCESSFUL_TURNS_KEY}:\s*(\d+)", mem.summary)
        if match:
            return int(match.group(1))
    return 0


class Aria(BaseAgent):
    id = "aria"

    def __init__(
        self,
        prompt_client: Optional[PromptRegistryClient] = None,
        gateway_client: Optional[LiteLLMGatewayClient] = None,
        turn_outcome_classifier: Optional[TurnOutcomeClassifier] = None,
    ) -> None:
        self._prompt_client = prompt_client or FilePromptRegistryClient(domain="mcat")
        self._gateway_client = gateway_client or default_gateway_client()
        self._turn_outcome_classifier = turn_outcome_classifier or KeywordTurnOutcomeClassifier()

    async def fetch_prompt(self) -> str:
        return self._prompt_client.get_prompt("aria", "v1")

    async def respond(self, input: AgentInput) -> AsyncIterator[AgentOutput]:
        is_medical = _is_medical_advice_request(input.message)

        concept_key = _infer_concept_key(input)
        already_assessed = _concept_previously_assessed(concept_key, input.episodic_context)

        system_prompt = await self.fetch_prompt() + ARIA_JSON_CONTRACT
        user_content = _build_user_content(input, concept_key, already_assessed)

        parsed = await complete_json(self._gateway_client, system_prompt, user_content)

        response_text = as_str(parsed.get("response"))
        if is_medical:
            response_text = (
                "I can't offer medical diagnosis or health advice -- that's outside what "
                "I'm able to help with. If you have a health concern, please talk to a "
                "medical professional. Let's get back to your MCAT prep, though. " + response_text
            ).strip()

        cited_chunks = valid_cited_chunks(parsed.get("cited_chunks"), input.retrieved_chunks)
        frustration_detected = as_bool(parsed.get("frustration_detected"))

        current_streak = _read_consecutive_successful_turns(input.episodic_context)
        turn_successful = self._turn_outcome_classifier.was_successful(input)
        new_streak = current_streak + 1 if turn_successful else 0

        suggested_handoff: Optional[str] = None
        if frustration_detected:
            suggested_handoff = "mira"
        elif new_streak >= 4:
            suggested_handoff = "quinn"

        # The medical guard is a hard safety boundary -- it always wins over
        # whatever risk_level the model itself reported.
        risk_level = "high" if is_medical else as_risk_level(parsed.get("risk_level"))

        yield AgentOutput(
            response=response_text,
            agent_id=self.id,
            cited_chunks=cited_chunks,
            suggested_handoff=suggested_handoff,
            mastery_update=None,
            session_notes=f"{SUCCESSFUL_TURNS_KEY}: {new_streak}",
            risk_level=risk_level,
        )

    async def write_episodic_memory(self, input: AgentInput, output: AgentOutput) -> None:
        # No persistence layer exists yet (paused core-data-schema epic).
        # Placeholder no-op -- see SPEC.md Out of Scope.
        return None


def _build_user_content(input: AgentInput, concept_key: str, already_assessed: bool) -> str:
    diagnostic_instruction = (
        "This concept has NOT been assessed with this student yet -- per your Socratic "
        "method, you MUST open with a diagnostic question, not an explanation."
        if not already_assessed
        else "This concept has already been assessed with this student in a prior turn "
        "(see episodic context below) -- skip the diagnostic opening and build directly "
        "on what they've already shown they know."
    )

    return (
        f"Student's message: {input.message}\n\n"
        f"Inferred concept: {concept_key}\n"
        f"{diagnostic_instruction}\n\n"
        f"Retrieved content (cite only what you actually use, via cited_chunks):\n"
        f"{render_chunks(input.retrieved_chunks)}\n\n"
        f"Episodic context (this student's history with this agent):\n"
        f"{render_episodic_context(input.episodic_context)}\n\n"
        f"Recent conversation this session:\n"
        f"{render_session_history(input.session_history)}"
    )
