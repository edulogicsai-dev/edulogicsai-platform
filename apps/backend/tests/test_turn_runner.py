import pytest

import domains.mcat.domain_config  # noqa: F401 -- self-registration
from domains._contracts.agent_io import AgentInput, AgentOutput, Message, StudentProfile
from domains._contracts.base_agent import BaseAgent
from domains._contracts.domain_config import AgentDef, DomainConfig, EvalRubric
from domains._contracts.domain_registry import DomainRegistry, registry
from nexus.graph_builder import build_graph
from nexus.graph_state import MAX_HOPS
from nexus.turn_runner import run_turn


def _base_input(**overrides) -> AgentInput:
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


FRUSTRATED_SESSION_HISTORY = [
    Message(role="user", content="I don't get it at all", timestamp="2026-01-01T00:00:00Z"),
    Message(role="assistant", content="Let's try again.", timestamp="2026-01-01T00:01:00Z"),
    Message(role="user", content="This is so frustrating", timestamp="2026-01-01T00:02:00Z"),
    Message(role="assistant", content="I hear you.", timestamp="2026-01-01T00:03:00Z"),
    Message(role="user", content="I give up, I'm lost", timestamp="2026-01-01T00:04:00Z"),
]


@pytest.mark.asyncio
async def test_aria_to_mira_handoff_with_no_cold_start() -> None:
    # AC2 -- real ARIA and MIRA, no mocks
    domain_result = registry.resolve_domain("mcat")
    graph = build_graph(domain_result.config, registry)

    agent_input = _base_input(session_history=FRUSTRATED_SESSION_HISTORY)
    result = await run_turn(
        graph, session_id="test-aria-mira", agent_input=agent_input, default_entry_agent_id="aria"
    )

    assert [o.agent_id for o in result.outputs] == ["aria", "mira"]
    aria_output, mira_output = result.outputs
    assert aria_output.suggested_handoff == "mira"
    # "No cold start": MIRA's response must reflect the dynamically-computed
    # session_notes ARIA produced THIS turn, not stale/fixture data.
    assert aria_output.session_notes in mira_output.response


class _AlwaysHandoffAgent(BaseAgent):
    def __init__(self, agent_id: str, target: str) -> None:
        self.id = agent_id
        self._target = target

    async def fetch_prompt(self) -> str:
        return ""

    async def respond(self, input: AgentInput):
        yield AgentOutput(
            response="loop",
            agent_id=self.id,
            cited_chunks=[],
            suggested_handoff=self._target,
            mastery_update=None,
            session_notes="",
            risk_level="low",
        )

    async def write_episodic_memory(self, input: AgentInput, output: AgentOutput) -> None:
        return None


@pytest.mark.asyncio
async def test_max_hops_safeguard_terminates_infinite_handoff_loop() -> None:
    # AC3
    fake_registry = DomainRegistry()
    fake_config = DomainConfig(
        id="loop-domain",
        name="Loop",
        subdomain="app.loop.test",
        agents=[
            AgentDef(id="ping", display_name="Ping", create_agent=lambda: _AlwaysHandoffAgent("ping", "pong")),
            AgentDef(id="pong", display_name="Pong", create_agent=lambda: _AlwaysHandoffAgent("pong", "ping")),
        ],
        content_index="loop_content",
        eval_rubric=EvalRubric(criteria=[]),
        theme={},
        escalation_rules=[],
    )
    fake_registry.register(fake_config)
    graph = build_graph(fake_config, fake_registry)

    agent_input = _base_input(tenant_id="loop-domain")
    result = await run_turn(
        graph, session_id="loop-session", agent_input=agent_input, default_entry_agent_id="ping"
    )

    assert len(result.outputs) == MAX_HOPS


@pytest.mark.asyncio
async def test_escalation_wins_over_simultaneous_handoff() -> None:
    # AC4 -- real ARIA can set both risk_level='high' and suggested_handoff on
    # one output (its medical-advice guard doesn't short-circuit the rest of
    # its logic), which is exactly the scenario this AC needs.
    domain_result = registry.resolve_domain("mcat")
    graph = build_graph(domain_result.config, registry)

    agent_input = _base_input(
        message="Do I have appendicitis based on this pain?",
        session_history=FRUSTRATED_SESSION_HISTORY,
    )
    result = await run_turn(
        graph, session_id="escalation-session", agent_input=agent_input, default_entry_agent_id="aria"
    )

    assert result.escalated is True
    assert [o.agent_id for o in result.outputs] == ["aria"]
    assert result.outputs[0].risk_level == "high"
    assert result.outputs[0].suggested_handoff == "mira"  # confirms both were set; escalation still won


@pytest.mark.asyncio
async def test_checkpoint_continuity_across_turns() -> None:
    # AC5
    domain_result = registry.resolve_domain("mcat")
    graph = build_graph(domain_result.config, registry)

    turn1_input = _base_input(session_history=FRUSTRATED_SESSION_HISTORY)
    result1 = await run_turn(
        graph, session_id="continuity-session", agent_input=turn1_input, default_entry_agent_id="aria"
    )
    assert [o.agent_id for o in result1.outputs] == ["aria", "mira"]
    assert result1.outputs[-1].suggested_handoff is None  # MIRA stays; no recovery signal yet

    turn2_input = _base_input(message="okay", session_history=[])
    result2 = await run_turn(
        graph, session_id="continuity-session", agent_input=turn2_input, default_entry_agent_id="aria"
    )
    assert result2.outputs[0].agent_id == "mira"  # resumes at MIRA, not the default entry agent
