"""
Live AgentInput assembly: student_profile/episodic_context/retrieved_chunks
from the database; session_history from an in-process cache, since no
messages table exists yet in core-data-schema to persist raw per-turn
transcripts durably. See
changes/2026/07/17/nexus-orchestration/changes/database-wiring/SPEC.md FR5,
Gaps & Assumptions, Open Questions.
"""

from domains._contracts.agent_io import AgentInput, Message
from db.repositories import DomainContentRepository, EpisodicMemoryRepository, StudentProfileRepository
from nexus.supervisor import assemble_agent_input

# In-process only -- lost on restart. See module docstring.
_session_history_cache: dict[str, list[Message]] = {}


def get_session_history(session_id: str) -> list[Message]:
    return _session_history_cache.get(session_id, [])


def append_to_session_history(session_id: str, message: Message) -> None:
    _session_history_cache.setdefault(session_id, []).append(message)


async def build_live_agent_input(
    tenant_id: str,
    student_id: str,
    session_id: str,
    message: str,
    student_profile_repo: StudentProfileRepository,
    episodic_repo: EpisodicMemoryRepository,
    content_repo: DomainContentRepository,
) -> AgentInput:
    student_profile = await student_profile_repo.load_profile(tenant_id, student_id)
    episodic_context = await episodic_repo.recent_for_student(tenant_id, student_id)
    retrieved_chunks = await content_repo.search(tenant_id, message)
    session_history = get_session_history(session_id)

    return assemble_agent_input(
        tenant_id=tenant_id,
        student_id=student_id,
        session_id=session_id,
        message=message,
        student_profile=student_profile,
        session_history=session_history,
        retrieved_chunks=retrieved_chunks,
        episodic_context=episodic_context,
    )
