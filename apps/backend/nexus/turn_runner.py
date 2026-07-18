"""
Ties graph_builder together with cross-turn checkpoint continuity: if the
session's last turn ended on a particular agent (no further handoff), the
next turn starts there instead of defaulting back to the entry agent. See
changes/2026/07/17/nexus-orchestration/changes/langgraph-state-machine/SPEC.md FR6.
"""

from dataclasses import dataclass

from langgraph.graph.state import CompiledStateGraph

from domains._contracts.agent_io import AgentInput, AgentOutput
from nexus.graph_state import GraphState


@dataclass
class TurnResult:
    outputs: list[AgentOutput]
    escalated: bool


async def run_turn(
    graph: CompiledStateGraph,
    session_id: str,
    agent_input: AgentInput,
    default_entry_agent_id: str,
) -> TurnResult:
    config = {"configurable": {"thread_id": session_id}}

    snapshot = await graph.aget_state(config)
    entry_agent_id = (
        snapshot.values.get("current_agent_id", default_entry_agent_id)
        if snapshot.values
        else default_entry_agent_id
    )

    initial_state = GraphState(
        agent_input=agent_input,
        current_agent_id=entry_agent_id,
        outputs=[],
        escalated=False,
        hops=0,
    )
    result = await graph.ainvoke(initial_state, config=config)

    return TurnResult(outputs=result["outputs"], escalated=result["escalated"])
