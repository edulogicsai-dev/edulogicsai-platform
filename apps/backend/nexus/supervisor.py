"""
NEXUS supervisor: assembles AgentInput from already-fetched components.
Actually fetching student_profile/session_history/retrieved_chunks/
episodic_context is database-wiring's job (a later change in this epic) --
this module defines the assembly contract, not the data access. See
changes/2026/07/17/nexus-orchestration/changes/nexus-supervisor/SPEC.md FR5.
"""

from domains._contracts.agent_io import AgentInput, ContentChunk, EpisodicMemory, Message, StudentProfile


def assemble_agent_input(
    tenant_id: str,
    student_id: str,
    session_id: str,
    message: str,
    student_profile: StudentProfile,
    session_history: list[Message],
    retrieved_chunks: list[ContentChunk],
    episodic_context: list[EpisodicMemory],
) -> AgentInput:
    return AgentInput(
        tenant_id=tenant_id,
        student_id=student_id,
        session_id=session_id,
        message=message,
        student_profile=student_profile,
        session_history=session_history,
        retrieved_chunks=retrieved_chunks,
        episodic_context=episodic_context,
    )
