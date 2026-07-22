import json

import pytest

from domains._contracts.agent_io import (
    AgentInput,
    ContentChunk,
    EpisodicMemory,
    Message,
    StudentProfile,
)
from domains.mcat.agents.aria import Aria


def make_input(**overrides) -> AgentInput:
    defaults = dict(
        tenant_id="mcat",
        student_id="student-1",
        session_id="session-1",
        message="Can you explain enzyme kinetics?",
        student_profile=StudentProfile(
            userId="student-1", displayName="Alex", createdAt="2026-01-01T00:00:00Z"
        ),
        session_history=[],
        retrieved_chunks=[],
        episodic_context=[],
    )
    defaults.update(overrides)
    return AgentInput(**defaults)


class _FakeGatewayClient:
    """Mocks the LLM call per test_intent_classifier.py's established
    pattern -- returns a fixed JSON payload as the model's completion."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    async def complete(self, model: str, messages: list[dict]) -> dict:
        return {"choices": [{"message": {"content": json.dumps(self._payload)}}]}


def make_aria(payload: dict) -> Aria:
    return Aria(gateway_client=_FakeGatewayClient(payload))


async def respond_once(input: AgentInput, payload: dict):
    aria = make_aria(payload)
    async for output in aria.respond(input):
        return output
    raise AssertionError("respond() yielded no output")


@pytest.mark.asyncio
async def test_opens_with_diagnostic_question_for_new_concept():
    # AC3: no prior episodic mention of this concept -> must open with a question.
    output = await respond_once(
        make_input(episodic_context=[]),
        {
            "response": "Before I explain, what do you already know about this?",
            "cited_chunks": [],
            "frustration_detected": False,
            "risk_level": "low",
        },
    )
    assert "?" in output.response or "what do you already know" in output.response.lower()


@pytest.mark.asyncio
async def test_skips_diagnostic_question_when_concept_already_assessed():
    input = make_input(
        retrieved_chunks=[
            ContentChunk(id="chunk-1", text="Enzyme kinetics...", sourceId="enzyme_kinetics", score=0.9)
        ],
        episodic_context=[
            EpisodicMemory(
                id="mem-1",
                summary="Discussed enzyme_kinetics in a prior session.",
                occurredAt="2026-01-01T00:00:00Z",
                relevanceScore=0.8,
            )
        ],
    )
    output = await respond_once(
        input,
        {
            "response": "Building on what we covered, here's a deeper look at the mechanism.",
            "cited_chunks": ["chunk-1"],
            "frustration_detected": False,
            "risk_level": "low",
        },
    )
    assert "what do you already know" not in output.response.lower()


@pytest.mark.asyncio
async def test_cites_retrieved_chunks_when_used():
    # AC4
    input = make_input(
        retrieved_chunks=[
            ContentChunk(id="chunk-1", text="...", sourceId="enzyme_kinetics", score=0.9),
            ContentChunk(id="chunk-2", text="...", sourceId="enzyme_kinetics", score=0.7),
        ]
    )
    output = await respond_once(
        input,
        {
            "response": "Here's the explanation, drawing on the retrieved material.",
            "cited_chunks": ["chunk-1", "chunk-2"],
            "frustration_detected": False,
            "risk_level": "low",
        },
    )
    assert output.cited_chunks == ["chunk-1", "chunk-2"]


@pytest.mark.asyncio
async def test_no_citations_when_no_chunks_retrieved():
    output = await respond_once(
        make_input(retrieved_chunks=[]),
        {
            # A hallucinated citation must still be filtered out -- there's
            # nothing valid to cite since nothing was retrieved.
            "response": "Let's work through this from general knowledge.",
            "cited_chunks": ["chunk-1"],
            "frustration_detected": False,
            "risk_level": "low",
        },
    )
    assert output.cited_chunks == []


@pytest.mark.asyncio
async def test_frustration_triggers_mira_handoff():
    # AC5: the model reports frustration_detected -- no keyword heuristic involved.
    session_history = [
        Message(role="user", content="I don't get it at all", timestamp="2026-01-01T00:00:00Z"),
        Message(role="assistant", content="Let's try again.", timestamp="2026-01-01T00:01:00Z"),
        Message(role="user", content="This is so frustrating", timestamp="2026-01-01T00:02:00Z"),
        Message(role="assistant", content="I hear you.", timestamp="2026-01-01T00:03:00Z"),
        Message(role="user", content="I give up, I'm lost", timestamp="2026-01-01T00:04:00Z"),
    ]
    output = await respond_once(
        make_input(session_history=session_history),
        {
            "response": "It sounds like this has been a lot -- let's pause on the content for a moment.",
            "cited_chunks": [],
            "frustration_detected": True,
            "risk_level": "medium",
        },
    )
    assert output.suggested_handoff == "mira"


@pytest.mark.asyncio
async def test_no_handoff_when_not_frustrated_or_ready():
    output = await respond_once(
        make_input(),
        {
            "response": "Let's start with what you already know.",
            "cited_chunks": [],
            "frustration_detected": False,
            "risk_level": "low",
        },
    )
    assert output.suggested_handoff is None


@pytest.mark.asyncio
async def test_readiness_after_four_successful_turns_triggers_quinn_handoff():
    # AC6: a prior streak of 3 + this turn being successful -> streak reaches 4.
    # Streak tracking is Python-side (deterministic), unaffected by the LLM call.
    input = make_input(
        message="Oh I see, that makes sense now.",
        episodic_context=[
            EpisodicMemory(
                id="mem-1",
                summary="consecutive_successful_turns: 3",
                occurredAt="2026-01-01T00:00:00Z",
                relevanceScore=0.5,
            )
        ],
    )
    output = await respond_once(
        input,
        {
            "response": "Great -- you've clearly got this one down.",
            "cited_chunks": [],
            "frustration_detected": False,
            "risk_level": "low",
        },
    )
    assert output.suggested_handoff == "quinn"
    assert "consecutive_successful_turns: 4" in output.session_notes


@pytest.mark.asyncio
async def test_medical_advice_request_declined_with_high_risk():
    # AC7: the guard is deterministic and wins regardless of what the model reports.
    input = make_input(message="Do I have appendicitis based on this pain?")
    output = await respond_once(
        input,
        {
            "response": "Let's get back to your MCAT prep.",
            "cited_chunks": [],
            "frustration_detected": False,
            "risk_level": "low",
        },
    )
    assert output.risk_level == "high"
    assert "can't offer medical diagnosis" in output.response.lower()


@pytest.mark.asyncio
async def test_medical_guard_wins_even_when_model_reports_low_risk_and_frustration_present():
    # Mirrors test_turn_runner.py's "escalation wins over simultaneous handoff":
    # ARIA can set both risk_level='high' (guard) and suggested_handoff='mira'
    # (frustration_detected) on the same output.
    session_history = [
        Message(role="user", content="I don't get it at all", timestamp="2026-01-01T00:00:00Z"),
        Message(role="user", content="This is so frustrating", timestamp="2026-01-01T00:02:00Z"),
        Message(role="user", content="I give up, I'm lost", timestamp="2026-01-01T00:04:00Z"),
    ]
    input = make_input(
        message="Do I have appendicitis based on this pain?",
        session_history=session_history,
    )
    output = await respond_once(
        input,
        {
            "response": "Let's get back to your MCAT prep.",
            "cited_chunks": [],
            "frustration_detected": True,
            "risk_level": "low",
        },
    )
    assert output.risk_level == "high"
    assert output.suggested_handoff == "mira"


@pytest.mark.asyncio
async def test_response_never_guarantees_a_score_or_skips_explanation():
    # AC8
    output = await respond_once(
        make_input(),
        {
            "response": "Students who master this tend to perform well on test day.",
            "cited_chunks": [],
            "frustration_detected": False,
            "risk_level": "low",
        },
    )
    lowered = output.response.lower()
    assert "guarantee" not in lowered
    assert "score of" not in lowered
    assert len(output.response.strip()) > 0


@pytest.mark.asyncio
async def test_malformed_model_response_raises_rather_than_silently_degrading():
    # req 7 / llm_support.py: a non-JSON completion is a real failure, left
    # to propagate -- sse-endpoint's existing try/except turns it into a
    # graceful `event: error`, so no swallowing happens here.
    from domains.mcat.agents.llm_support import LLMResponseParseError

    class _BrokenGatewayClient:
        async def complete(self, model: str, messages: list[dict]) -> dict:
            return {"choices": [{"message": {"content": "not json at all"}}]}

    aria = Aria(gateway_client=_BrokenGatewayClient())
    with pytest.raises(LLMResponseParseError):
        async for _ in aria.respond(make_input()):
            pass
