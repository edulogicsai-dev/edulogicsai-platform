"""
PersistentAgent wraps any BaseAgent, replacing only write_episodic_memory()
with a real database write -- zero changes needed to BaseAgent.stream() or
the wrapped agent itself. See
changes/2026/07/17/nexus-orchestration/changes/database-wiring/SPEC.md FR3, FR4.
"""

from typing import AsyncIterator

from db.repositories import ConceptMasteryRepository, EpisodicMemoryRepository
from domains._contracts.agent_io import AgentInput, AgentOutput
from domains._contracts.base_agent import BaseAgent


class PersistentAgent(BaseAgent):
    def __init__(self, inner: BaseAgent, episodic_repo: EpisodicMemoryRepository) -> None:
        self.id = inner.id
        self._inner = inner
        self._episodic_repo = episodic_repo

    async def fetch_prompt(self) -> str:
        return await self._inner.fetch_prompt()

    def respond(self, input: AgentInput) -> AsyncIterator[AgentOutput]:
        return self._inner.respond(input)

    async def write_episodic_memory(self, input: AgentInput, output: AgentOutput) -> None:
        await self._episodic_repo.write(
            tenant_id=input.tenant_id,
            student_id=input.student_id,
            session_id=input.session_id,
            summary=output.session_notes,
        )


class QuinnPersistentAgent(PersistentAgent):
    def __init__(
        self,
        inner: BaseAgent,
        episodic_repo: EpisodicMemoryRepository,
        mastery_repo: ConceptMasteryRepository,
    ) -> None:
        super().__init__(inner, episodic_repo)
        self._mastery_repo = mastery_repo

    async def write_episodic_memory(self, input: AgentInput, output: AgentOutput) -> None:
        await super().write_episodic_memory(input, output)
        if output.mastery_update is not None:
            # newStability > previousStability means the ease-factor-repurposed
            # delta went up, i.e. the answer was correct -- see quinn.py.
            correct = output.mastery_update.newStability > output.mastery_update.previousStability
            await self._mastery_repo.record_attempt(
                tenant_id=input.tenant_id,
                student_id=input.student_id,
                concept_id=output.mastery_update.conceptId,
                correct=correct,
            )
