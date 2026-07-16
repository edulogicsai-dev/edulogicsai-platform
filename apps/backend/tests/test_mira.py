import pytest

from domains._contracts.agent_io import AgentInput, EpisodicMemory, Message, StudentProfile
from domains.mcat.agents.mira import Mira


def make_input(**overrides) -> AgentInput:
    defaults = dict(
        tenant_id="mcat",
        student_id="student-1",
        session_id="session-1",
        message="I don't get enzyme kinetics at all.",
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
    mira = Mira()
    async for output in mira.respond(input):
        return output
    raise AssertionError("respond() yielded no output")


@pytest.mark.asyncio
async def test_acknowledges_specific_struggle_from_episodic_context():
    # AC1
    input = make_input(
        episodic_context=[
            EpisodicMemory(
                id="mem-1",
                summary="enzyme kinetics",
                occurredAt="2026-01-01T00:00:00Z",
                relevanceScore=0.8,
            )
        ]
    )
    output = await respond_once(input)
    assert "enzyme kinetics" in output.response.lower()


@pytest.mark.asyncio
async def test_validates_effort_and_offers_one_strategy():
    # AC2
    output = await respond_once(make_input())
    lowered = output.response.lower()
    assert "effort" in lowered
    # exactly one strategy sentence -- no enumerated list of multiple options
    assert lowered.count("here's one thing") == 1


@pytest.mark.asyncio
async def test_recovery_signals_trigger_aria_handoff():
    # AC3
    session_history = [
        Message(role="user", content="Feeling better now", timestamp="2026-01-01T00:00:00Z"),
        Message(role="assistant", content="Glad to hear it.", timestamp="2026-01-01T00:01:00Z"),
        Message(role="user", content="Okay let's try again", timestamp="2026-01-01T00:02:00Z"),
    ]
    output = await respond_once(make_input(session_history=session_history))
    assert output.suggested_handoff == "aria"


@pytest.mark.asyncio
async def test_high_distress_sets_risk_level_high():
    # AC4
    session_history = [
        Message(role="user", content="I'm a failure, nothing works", timestamp="2026-01-01T00:00:00Z"),
        Message(role="user", content="I want to quit, what's the point", timestamp="2026-01-01T00:01:00Z"),
    ]
    output = await respond_once(make_input(session_history=session_history))
    assert output.risk_level == "high"


@pytest.mark.asyncio
async def test_never_hands_off_to_quinn():
    # AC5
    scenarios = [
        make_input(),
        make_input(
            session_history=[
                Message(role="user", content="Feeling better now", timestamp="2026-01-01T00:00:00Z"),
            ]
        ),
        make_input(
            session_history=[
                Message(role="user", content="I'm a failure, nothing works", timestamp="2026-01-01T00:00:00Z"),
                Message(role="user", content="I can't take it, what's the point", timestamp="2026-01-01T00:01:00Z"),
            ]
        ),
    ]
    for input in scenarios:
        output = await respond_once(input)
        assert output.suggested_handoff != "quinn"


@pytest.mark.asyncio
async def test_distress_takes_priority_over_simultaneous_recovery_signal():
    # AC6
    session_history = [
        Message(role="user", content="I'm a failure, nothing works", timestamp="2026-01-01T00:00:00Z"),
        Message(role="user", content="Feeling better now", timestamp="2026-01-01T00:01:00Z"),
    ]
    # craft distress > 0.85 by having both recent messages carry distress markers
    session_history = [
        Message(role="user", content="I'm a failure, what's the point", timestamp="2026-01-01T00:00:00Z"),
        Message(role="user", content="nothing works, i want to quit but feeling better now", timestamp="2026-01-01T00:01:00Z"),
    ]
    output = await respond_once(make_input(session_history=session_history))
    assert output.risk_level == "high"
    assert output.suggested_handoff is None


@pytest.mark.asyncio
async def test_never_minimizes_pushes_content_or_promises_outcomes():
    # AC7
    output = await respond_once(make_input())
    lowered = output.response.lower()
    assert "it's not that hard" not in lowered
    assert "it's not a big deal" not in lowered
    assert "just relax" not in lowered
    assert "you'll feel better" not in lowered
