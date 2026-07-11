"""
ARIA -- the primary adaptive Socratic tutor for MCATai.
See changes/2026/07/10/aria-agent/SPEC.md (FR3-FR5) and
domains/mcat/prompts/aria_v1.md for ARIA's authored system prompt.

Frustration/readiness/concept-mastery detection here are interim keyword
heuristics (SPEC.md FR4 and Gaps & Assumptions) behind swappable protocols,
pending a real SentimentTool / concept_mastery DB integration.
"""

import re
from typing import AsyncIterator, Optional, Protocol

from domains._contracts.agent_io import AgentInput, AgentOutput, EpisodicMemory, Message
from domains._contracts.base_agent import BaseAgent
from prompt_registry.client import FilePromptRegistryClient, PromptRegistryClient

MEDICAL_ADVICE_PATTERNS = [
    r"\bshould i (take|see a doctor)\b",
    r"\bdo i have\b",
    r"\bwhat medication\b",
    r"\bcan you diagnose\b",
    r"\bmy (symptom|diagnosis|prescription)\b",
]

FRUSTRATION_MARKERS = [
    "i give up",
    "this is so frustrating",
    "i don't get it",
    "i hate this",
    "so confused",
    "i'm lost",
    "why is this so hard",
]

SUCCESS_MARKERS = [
    "that makes sense",
    "i understand",
    "got it",
    "oh i see",
    "that helps",
]

SUCCESSFUL_TURNS_KEY = "consecutive_successful_turns"


class FrustrationEstimator(Protocol):
    def estimate(self, recent_user_messages: list[Message]) -> float: ...


class TurnOutcomeClassifier(Protocol):
    def was_successful(self, input: AgentInput) -> bool: ...


class KeywordFrustrationEstimator:
    """Interim heuristic -- see SPEC.md FR4. Replace with SentimentTool later."""

    def estimate(self, recent_user_messages: list[Message]) -> float:
        if not recent_user_messages:
            return 0.0
        hits = sum(
            1
            for msg in recent_user_messages
            if any(marker in msg.content.lower() for marker in FRUSTRATION_MARKERS)
        )
        return hits / len(recent_user_messages)


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
        frustration_estimator: Optional[FrustrationEstimator] = None,
        turn_outcome_classifier: Optional[TurnOutcomeClassifier] = None,
    ) -> None:
        self._prompt_client = prompt_client or FilePromptRegistryClient(domain="mcat")
        self._frustration_estimator = frustration_estimator or KeywordFrustrationEstimator()
        self._turn_outcome_classifier = turn_outcome_classifier or KeywordTurnOutcomeClassifier()

    async def fetch_prompt(self) -> str:
        return self._prompt_client.get_prompt("aria", "v1")

    async def respond(self, input: AgentInput) -> AsyncIterator[AgentOutput]:
        response_parts: list[str] = []
        risk_level = "low"

        if _is_medical_advice_request(input.message):
            response_parts.append(
                "I can't offer medical diagnosis or health advice -- that's outside what "
                "I'm able to help with. If you have a health concern, please talk to a "
                "medical professional. Let's get back to your MCAT prep, though."
            )
            risk_level = "high"

        concept_key = _infer_concept_key(input)
        already_assessed = _concept_previously_assessed(concept_key, input.episodic_context)

        if not already_assessed:
            response_parts.append(
                f"Before I explain, let's check your starting point on this -- "
                f"what do you already know here?"
            )
        else:
            prior_mentions = sum(
                1 for mem in input.episodic_context if concept_key in mem.summary.lower()
            )
            depth = "a foundational, step-by-step" if prior_mentions <= 1 else "a concise, higher-level"
            response_parts.append(f"Here's {depth} explanation, building on what we've covered.")

        cited_chunks: list[str] = []
        if input.retrieved_chunks:
            cited_chunks = [chunk.id for chunk in input.retrieved_chunks]
            sources = ", ".join(chunk.sourceId for chunk in input.retrieved_chunks)
            response_parts.append(f"(Drawing on: {sources})")

        recent_user_messages = [m for m in input.session_history if m.role == "user"][-3:]
        frustration_score = self._frustration_estimator.estimate(recent_user_messages)

        current_streak = _read_consecutive_successful_turns(input.episodic_context)
        turn_successful = self._turn_outcome_classifier.was_successful(input)
        new_streak = current_streak + 1 if turn_successful else 0

        suggested_handoff: Optional[str] = None
        if frustration_score > 0.6:
            suggested_handoff = "mira"
        elif new_streak >= 4:
            suggested_handoff = "quinn"

        yield AgentOutput(
            response=" ".join(response_parts),
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
