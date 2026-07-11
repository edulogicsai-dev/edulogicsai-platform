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


async def respond_once(input: AgentInput):
    aria = Aria()
    async for output in aria.respond(input):
        return output
    raise AssertionError("respond() yielded no output")


@pytest.mark.asyncio
async def test_opens_with_diagnostic_question_for_new_concept():
    # AC3: no prior episodic mention of this concept -> must open with a question.
    output = await respond_once(make_input(episodic_context=[]))
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
    output = await respond_once(input)
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
    output = await respond_once(input)
    assert output.cited_chunks == ["chunk-1", "chunk-2"]


@pytest.mark.asyncio
async def test_no_citations_when_no_chunks_retrieved():
    output = await respond_once(make_input(retrieved_chunks=[]))
    assert output.cited_chunks == []


@pytest.mark.asyncio
async def test_frustration_triggers_mira_handoff():
    # AC5: last 3 user messages score above frustration threshold.
    session_history = [
        Message(role="user", content="I don't get it at all", timestamp="2026-01-01T00:00:00Z"),
        Message(role="assistant", content="Let's try again.", timestamp="2026-01-01T00:01:00Z"),
        Message(role="user", content="This is so frustrating", timestamp="2026-01-01T00:02:00Z"),
        Message(role="assistant", content="I hear you.", timestamp="2026-01-01T00:03:00Z"),
        Message(role="user", content="I give up, I'm lost", timestamp="2026-01-01T00:04:00Z"),
    ]
    output = await respond_once(make_input(session_history=session_history))
    assert output.suggested_handoff == "mira"


@pytest.mark.asyncio
async def test_no_handoff_when_not_frustrated_or_ready():
    output = await respond_once(make_input())
    assert output.suggested_handoff is None


@pytest.mark.asyncio
async def test_readiness_after_four_successful_turns_triggers_quinn_handoff():
    # AC6: a prior streak of 3 + this turn being successful -> streak reaches 4.
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
    output = await respond_once(input)
    assert output.suggested_handoff == "quinn"
    assert "consecutive_successful_turns: 4" in output.session_notes


@pytest.mark.asyncio
async def test_medical_advice_request_declined_with_high_risk():
    # AC7
    input = make_input(message="Do I have appendicitis based on this pain?")
    output = await respond_once(input)
    assert output.risk_level == "high"
    assert "can't offer medical diagnosis" in output.response.lower()


@pytest.mark.asyncio
async def test_response_never_guarantees_a_score_or_skips_explanation():
    # AC8
    output = await respond_once(make_input())
    lowered = output.response.lower()
    assert "guarantee" not in lowered
    assert "score of" not in lowered
    assert len(output.response.strip()) > 0
