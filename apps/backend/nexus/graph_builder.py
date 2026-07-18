"""
Dynamic LangGraph construction: one node per agent in domain_config.agents,
edges conditioned on AgentOutput.suggested_handoff, in-turn context folding
(no cold starts), HITL escalation short-circuit, max-hops safeguard. See
changes/2026/07/17/nexus-orchestration/changes/langgraph-state-machine/SPEC.md.
"""

import datetime
import logging

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from domains._contracts.agent_io import EpisodicMemory
from domains._contracts.domain_config import DomainConfig
from domains._contracts.domain_registry import DomainRegistry
from nexus.graph_state import MAX_HOPS, GraphState

logger = logging.getLogger(__name__)


def _fold_output_into_input(agent_input, agent_id: str, output):
    new_memory = EpisodicMemory(
        id=f"turn-{agent_id}-{len(agent_input.episodic_context)}",
        summary=output.session_notes or f"{agent_id}: {output.response[:100]}",
        occurredAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        relevanceScore=1.0,
    )
    return agent_input.model_copy(update={"episodic_context": agent_input.episodic_context + [new_memory]})


def _make_node(agent_id: str, domain_id: str, registry: DomainRegistry):
    async def node(state: GraphState) -> dict:
        agent = registry.resolve_agent(domain_id, agent_id)
        output = None
        async for chunk in agent.respond(state.agent_input):
            output = chunk
        assert output is not None, f"{agent_id}.respond() yielded no output"

        escalated = output.risk_level == "high"
        if escalated:
            logger.warning("HITL escalation: agent_id=%s output=%r", agent_id, output)

        next_input = _fold_output_into_input(state.agent_input, agent_id, output)

        return {
            "agent_input": next_input,
            "current_agent_id": agent_id,
            "outputs": state.outputs + [output],
            "escalated": escalated,
            "hops": state.hops + 1,
        }

    return node


def build_graph(domain_config: DomainConfig, registry: DomainRegistry) -> CompiledStateGraph:
    graph = StateGraph(GraphState)

    valid_agent_ids = {a.id for a in domain_config.agents}

    for agent_def in domain_config.agents:
        graph.add_node(agent_def.id, _make_node(agent_def.id, domain_config.id, registry))

    def entry_route(state: GraphState) -> str:
        return state.current_agent_id

    entry_map = {a.id: a.id for a in domain_config.agents}
    graph.add_conditional_edges(START, entry_route, entry_map)

    def handoff_route(state: GraphState) -> str:
        if state.escalated:
            return END
        if state.hops >= MAX_HOPS:
            return END
        last_output = state.outputs[-1] if state.outputs else None
        if last_output and last_output.suggested_handoff and last_output.suggested_handoff in valid_agent_ids:
            return last_output.suggested_handoff
        return END

    handoff_map = {**{a.id: a.id for a in domain_config.agents}, END: END}
    for agent_def in domain_config.agents:
        graph.add_conditional_edges(agent_def.id, handoff_route, handoff_map)

    return graph.compile(checkpointer=MemorySaver())
