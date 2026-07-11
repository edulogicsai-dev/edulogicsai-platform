"""
Mirrors packages/core/src/agent/base-agent.ts's control flow. Python agents
extend THIS class (not the TypeScript one -- cross-language inheritance is
impossible). Per CLAUDE.md's Agent Contract Architecture: this is the
IMPLEMENTATION-side counterpart to the TypeScript CONTRACT.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator

from domains._contracts.agent_io import AgentInput, AgentOutput


class BaseAgent(ABC):
    id: str

    @abstractmethod
    async def fetch_prompt(self) -> str:
        """Fetch this agent's versioned system prompt from PromptRegistry. Never hardcoded."""

    @abstractmethod
    def respond(self, input: AgentInput) -> AsyncIterator[AgentOutput]:
        """Produce a streamed sequence of AgentOutput chunks for the given input."""

    @abstractmethod
    async def write_episodic_memory(self, input: AgentInput, output: AgentOutput) -> None:
        """Persist this turn's output to episodic memory (Mem0 + pgvector)."""

    async def stream(self, input: AgentInput) -> AsyncIterator[AgentOutput]:
        """
        Orchestrates one full turn: fetch this agent's prompt, stream the
        response, then persist to episodic memory. Callers use this, not
        respond() directly -- mirrors the TypeScript BaseAgent's stream().
        """
        await self.fetch_prompt()
        last: AgentOutput | None = None
        async for chunk in self.respond(input):
            last = chunk
            yield chunk
        if last is not None:
            await self.write_episodic_memory(input, last)
