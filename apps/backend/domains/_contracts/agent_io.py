"""
Pydantic mirrors of packages/core/src/agent/*.ts (TypeScript).
Field names/types must match exactly -- see tests/test_agent_io_contracts.py
and CLAUDE.md's Agent Contract Architecture section. Python cannot literally
extend the TypeScript types; shape equivalence is enforced by that test.
"""

from typing import Literal, Optional

from pydantic import BaseModel

RiskLevel = Literal["low", "medium", "high"]


class StudentProfile(BaseModel):
    userId: str
    displayName: str
    createdAt: str


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: str


class ContentChunk(BaseModel):
    id: str
    text: str
    sourceId: str
    score: float


class EpisodicMemory(BaseModel):
    id: str
    summary: str
    occurredAt: str
    relevanceScore: float


class MasteryDelta(BaseModel):
    conceptId: str
    previousStability: float
    newStability: float
    reviewedAt: str


class AgentInput(BaseModel):
    tenant_id: str
    student_id: str
    session_id: str
    message: str
    student_profile: StudentProfile
    session_history: list[Message]
    retrieved_chunks: list[ContentChunk]
    episodic_context: list[EpisodicMemory]


class AgentOutput(BaseModel):
    response: str
    agent_id: str
    cited_chunks: list[str]
    suggested_handoff: Optional[str]
    mastery_update: Optional[MasteryDelta]
    session_notes: str
    risk_level: RiskLevel
