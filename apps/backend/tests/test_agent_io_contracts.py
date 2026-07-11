"""
Asserts the Pydantic AgentInput/AgentOutput field sets match the documented
reference list in SPEC.md FR2 (mirroring packages/core/src/agent/*.ts).
If either the TypeScript or Python side changes without the other, this
fails -- see changes/2026/07/10/aria-agent/SPEC.md FR2.
"""

from domains._contracts.agent_io import AgentInput, AgentOutput

EXPECTED_AGENT_INPUT_FIELDS = {
    "tenant_id",
    "student_id",
    "session_id",
    "message",
    "student_profile",
    "session_history",
    "retrieved_chunks",
    "episodic_context",
}

EXPECTED_AGENT_OUTPUT_FIELDS = {
    "response",
    "agent_id",
    "cited_chunks",
    "suggested_handoff",
    "mastery_update",
    "session_notes",
    "risk_level",
}


def test_agent_input_field_parity() -> None:
    assert set(AgentInput.model_fields.keys()) == EXPECTED_AGENT_INPUT_FIELDS


def test_agent_output_field_parity() -> None:
    assert set(AgentOutput.model_fields.keys()) == EXPECTED_AGENT_OUTPUT_FIELDS
