from pydantic import BaseModel

from domains._contracts.agent_io import AgentInput, AgentOutput

MAX_HOPS = 3


class GraphState(BaseModel):
    agent_input: AgentInput
    current_agent_id: str
    outputs: list[AgentOutput] = []
    escalated: bool = False
    hops: int = 0
