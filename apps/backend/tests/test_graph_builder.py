from domains._contracts.agent_io import AgentInput, AgentOutput
from domains._contracts.base_agent import BaseAgent
from domains._contracts.domain_config import AgentDef, DomainConfig, EvalRubric
from domains._contracts.domain_registry import DomainRegistry
from nexus.graph_builder import build_graph


class _FakeAgent(BaseAgent):
    def __init__(self, agent_id: str) -> None:
        self.id = agent_id

    async def fetch_prompt(self) -> str:
        return ""

    async def respond(self, input: AgentInput):
        yield AgentOutput(
            response="ok",
            agent_id=self.id,
            cited_chunks=[],
            suggested_handoff=None,
            mastery_update=None,
            session_notes="",
            risk_level="low",
        )

    async def write_episodic_memory(self, input: AgentInput, output: AgentOutput) -> None:
        return None


def _fake_domain_config(domain_id: str, agent_ids: list[str]) -> DomainConfig:
    return DomainConfig(
        id=domain_id,
        name=domain_id,
        subdomain=f"app.{domain_id}.test",
        agents=[
            AgentDef(id=aid, display_name=aid, create_agent=lambda aid=aid: _FakeAgent(aid))
            for aid in agent_ids
        ],
        content_index=f"{domain_id}_content",
        eval_rubric=EvalRubric(criteria=[]),
        theme={},
        escalation_rules=[],
    )


def _node_ids(compiled_graph) -> set[str]:
    all_nodes = set(compiled_graph.get_graph().nodes.keys())
    return all_nodes - {"__start__", "__end__"}


def test_build_graph_produces_different_node_sets_for_different_domains() -> None:
    # AC1
    registry_a = DomainRegistry()
    config_a = _fake_domain_config("domain-a", ["x", "y"])
    registry_a.register(config_a)
    graph_a = build_graph(config_a, registry_a)

    registry_b = DomainRegistry()
    config_b = _fake_domain_config("domain-b", ["p", "q", "r"])
    registry_b.register(config_b)
    graph_b = build_graph(config_b, registry_b)

    assert _node_ids(graph_a) == {"x", "y"}
    assert _node_ids(graph_b) == {"p", "q", "r"}
    assert _node_ids(graph_a) != _node_ids(graph_b)
