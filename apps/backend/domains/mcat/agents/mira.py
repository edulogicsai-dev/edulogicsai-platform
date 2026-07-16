"""
MIRA -- the Motivation & Resilience Coach for MCATai.
See changes/2026/07/15/mira-agent/SPEC.md (FR1-FR4) and
domains/mcat/prompts/mira_v1.md for MIRA's authored system prompt.

Distress/recovery detection here are interim keyword heuristics
(SPEC.md FR3 and Gaps & Assumptions) behind swappable protocols, matching
the pattern established for ARIA (changes/2026/07/10/aria-agent/).
"""

import re
from typing import AsyncIterator, List, Optional, Protocol

from domains._contracts.agent_io import AgentInput, AgentOutput, EpisodicMemory, Message
from domains._contracts.base_agent import BaseAgent
from prompt_registry.client import FilePromptRegistryClient, PromptRegistryClient

DISTRESS_MARKERS = [
    "i can't do this anymore",
    "i'm worthless",
    "what's the point",
    "i want to quit",
    "i'm a failure",
    "nothing works",
    "i can't take it",
]

RECOVERY_MARKERS = [
    "feeling better",
    "okay let's try again",
    "i'm ready",
    "thanks, that helps",
    "i feel calmer",
    "let's continue",
]

MINIMIZING_PHRASES = ["it's not that hard", "it's not a big deal", "just relax"]


class DistressEstimator(Protocol):
    def estimate(self, recent_user_messages: List[Message]) -> float: ...


class RecoverySignalClassifier(Protocol):
    def detect(self, recent_user_messages: List[Message]) -> bool: ...


class KeywordDistressEstimator:
    """Interim heuristic -- see SPEC.md FR3. Replace with a real signal later."""

    def estimate(self, recent_user_messages: List[Message]) -> float:
        if not recent_user_messages:
            return 0.0
        hits = sum(
            1
            for msg in recent_user_messages
            if any(marker in msg.content.lower() for marker in DISTRESS_MARKERS)
        )
        return hits / len(recent_user_messages)


class KeywordRecoverySignalClassifier:
    """Interim heuristic -- see SPEC.md FR3. Replace with a real signal later."""

    def detect(self, recent_user_messages: List[Message]) -> bool:
        return any(
            any(marker in msg.content.lower() for marker in RECOVERY_MARKERS)
            for msg in recent_user_messages
        )


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
        distress_estimator: Optional[DistressEstimator] = None,
        recovery_classifier: Optional[RecoverySignalClassifier] = None,
    ) -> None:
        self._prompt_client = prompt_client or FilePromptRegistryClient(domain="mcat")
        self._distress_estimator = distress_estimator or KeywordDistressEstimator()
        self._recovery_classifier = recovery_classifier or KeywordRecoverySignalClassifier()

    async def fetch_prompt(self) -> str:
        return self._prompt_client.get_prompt("mira", "v1")

    async def respond(self, input: AgentInput) -> AsyncIterator[AgentOutput]:
        handoff_cause = _find_handoff_cause(input.episodic_context, input.message)

        response_parts = [
            f"I hear you -- {handoff_cause} is genuinely hard, and you've been putting in real effort on it.",
            "That effort matters, regardless of how it's gone so far.",
            "Here's one thing that might help right now: take a short break, then come back to it "
            "with a simpler version of the idea.",
        ]

        recent_user_messages = [m for m in input.session_history if m.role == "user"][-2:]
        distress_score = self._distress_estimator.estimate(recent_user_messages)
        recovered = self._recovery_classifier.detect(recent_user_messages)

        risk_level = "low"
        suggested_handoff: Optional[str] = None

        if distress_score > 0.85:
            # Safety takes priority over a simultaneous recovery signal.
            risk_level = "high"
            response_parts.append(
                "What you're carrying sounds like more than I'm equipped to help with alone -- "
                "I want to make sure a person can check in with you about this."
            )
        elif recovered:
            suggested_handoff = "aria"

        yield AgentOutput(
            response=" ".join(response_parts),
            agent_id=self.id,
            cited_chunks=[],
            suggested_handoff=suggested_handoff,
            mastery_update=None,
            session_notes=f"distress_score: {distress_score:.2f}",
            risk_level=risk_level,
        )

    async def write_episodic_memory(self, input: AgentInput, output: AgentOutput) -> None:
        # No persistence layer exists yet (paused core-data-schema epic).
        # Placeholder no-op -- see SPEC.md Out of Scope.
        return None
