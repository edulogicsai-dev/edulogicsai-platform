from domains._contracts.agent_io import StudentProfile
from nexus.supervisor import assemble_agent_input


def test_assemble_agent_input_builds_valid_agent_input() -> None:
    # AC6
    result = assemble_agent_input(
        tenant_id="mcat",
        student_id="student-1",
        session_id="session-1",
        message="hello",
        student_profile=StudentProfile(userId="student-1", displayName="Alex", createdAt="2026-01-01T00:00:00Z"),
        session_history=[],
        retrieved_chunks=[],
        episodic_context=[],
    )
    assert result.tenant_id == "mcat"
    assert result.student_id == "student-1"
    assert result.message == "hello"
