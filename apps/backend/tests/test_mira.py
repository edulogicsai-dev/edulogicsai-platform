import json

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


class _FakeGatewayClient:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    async def complete(self, model: str, messages: list[dict]) -> dict:
        return {"choices": [{"message": {"content": json.dumps(self._payload)}}]}


async def respond_once(input: AgentInput, payload: dict):
    mira = Mira(gateway_client=_FakeGatewayClient(payload))
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
    output = await respond_once(
        input,
        {
            "response": "Enzyme kinetics is genuinely one of the toughest topics -- struggling with it doesn't mean you're behind.",
            "recovered": False,
            "risk_level": "low",
            "session_notes": "Student frustrated with enzyme kinetics; offered a break.",
        },
    )
    assert "enzyme kinetics" in output.response.lower()


@pytest.mark.asyncio
async def test_validates_effort_and_offers_one_strategy():
    # AC2
    output = await respond_once(
        make_input(),
        {
            "response": (
                "This is genuinely hard, and the effort you've put in matters. "
                "Here's one thing that might help: take a short break and come back to it."
            ),
            "recovered": False,
            "risk_level": "low",
            "session_notes": "Offered a break.",
        },
    )
    lowered = output.response.lower()
    assert "effort" in lowered
    assert lowered.count("here's one thing") == 1


@pytest.mark.asyncio
async def test_recovery_signals_trigger_aria_handoff():
    # AC3
    session_history = [
        Message(role="user", content="Feeling better now", timestamp="2026-01-01T00:00:00Z"),
        Message(role="assistant", content="Glad to hear it.", timestamp="2026-01-01T00:01:00Z"),
        Message(role="user", content="Okay let's try again", timestamp="2026-01-01T00:02:00Z"),
    ]
    output = await respond_once(
        make_input(session_history=session_history),
        {
            "response": "Glad to hear it -- let's pick back up with ARIA.",
            "recovered": True,
            "risk_level": "low",
            "session_notes": "Student recovered, ready to continue.",
        },
    )
    assert output.suggested_handoff == "aria"


@pytest.mark.asyncio
async def test_high_distress_sets_risk_level_high():
    # AC4
    session_history = [
        Message(role="user", content="I'm a failure, nothing works", timestamp="2026-01-01T00:00:00Z"),
        Message(role="user", content="I want to quit, what's the point", timestamp="2026-01-01T00:01:00Z"),
    ]
    output = await respond_once(
        make_input(session_history=session_history),
        {
            "response": "What you're carrying sounds like more than I'm equipped to help with alone.",
            "recovered": False,
            "risk_level": "high",
            "session_notes": "Genuine distress signals -- escalated.",
        },
    )
    assert output.risk_level == "high"


@pytest.mark.asyncio
async def test_never_hands_off_to_quinn():
    # AC5 -- MIRA's suggested_handoff can only ever be "aria" or None by
    # construction (there's no code path that could set "quinn").
    for recovered in (False, True):
        output = await respond_once(
            make_input(),
            {
                "response": "Coaching response.",
                "recovered": recovered,
                "risk_level": "low",
                "session_notes": "note",
            },
        )
        assert output.suggested_handoff != "quinn"


@pytest.mark.asyncio
async def test_distress_takes_priority_over_simultaneous_recovery_signal():
    # AC6 -- even if the model reports both signals, high risk wins.
    session_history = [
        Message(role="user", content="I'm a failure, what's the point", timestamp="2026-01-01T00:00:00Z"),
        Message(
            role="user",
            content="nothing works, i want to quit but feeling better now",
            timestamp="2026-01-01T00:01:00Z",
        ),
    ]
    output = await respond_once(
        make_input(session_history=session_history),
        {
            "response": "I want to make sure a person can check in with you about this.",
            "recovered": True,
            "risk_level": "high",
            "session_notes": "Distress signals present despite mixed language.",
        },
    )
    assert output.risk_level == "high"
    assert output.suggested_handoff is None


@pytest.mark.asyncio
async def test_never_minimizes_pushes_content_or_promises_outcomes():
    # AC7
    output = await respond_once(
        make_input(),
        {
            "response": "This is hard, and that's real. A short break might help, but no promises on timing.",
            "recovered": False,
            "risk_level": "low",
            "session_notes": "note",
        },
    )
    lowered = output.response.lower()
    assert "it's not that hard" not in lowered
    assert "it's not a big deal" not in lowered
    assert "just relax" not in lowered
    assert "you'll feel better" not in lowered
