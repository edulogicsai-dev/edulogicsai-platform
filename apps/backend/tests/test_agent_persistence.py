import os
import uuid

import asyncpg
import pytest

from db.agent_persistence import PersistentAgent, QuinnPersistentAgent
from db.repositories import AgentSessionRepository, ConceptMasteryRepository, EpisodicMemoryRepository
from domains._contracts.agent_io import AgentInput, EpisodicMemory, StudentProfile
from domains.mcat.agents.aria import Aria
from domains.mcat.agents.quinn import Quinn

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://app_backend@localhost/edulogicsai_nexus_test"
)
SEED_DATABASE_URL = os.environ.get("SEED_DATABASE_URL", "postgresql:///edulogicsai_nexus_test")

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def pool():
    p = await asyncpg.create_pool(TEST_DATABASE_URL)
    yield p
    await p.close()


@pytest.fixture
async def seed_conn():
    conn = await asyncpg.connect(SEED_DATABASE_URL)
    yield conn
    await conn.close()


async def _seed_student_with_session(seed_conn: asyncpg.Connection, pool: asyncpg.Pool) -> tuple[str, str]:
    student_id = str(uuid.uuid4())
    await seed_conn.execute("insert into auth.users (id) values ($1)", student_id)
    await seed_conn.execute(
        "insert into student_profiles (user_id, tenant_id) values ($1, 'mcat')", student_id
    )
    session_repo = AgentSessionRepository(pool)
    session_id = await session_repo.create_session(tenant_id="mcat", student_id=student_id, agent_id="aria")
    return student_id, session_id


def _make_input(student_id: str, session_id: str, **overrides) -> AgentInput:
    defaults = dict(
        tenant_id="mcat",
        student_id=student_id,
        session_id=session_id,
        message="Can you explain enzyme kinetics?",
        student_profile=StudentProfile(userId=student_id, displayName="Alex", createdAt="2026-01-01T00:00:00Z"),
        session_history=[],
        retrieved_chunks=[],
        episodic_context=[],
    )
    defaults.update(overrides)
    return AgentInput(**defaults)


async def test_persistent_agent_writes_real_episodic_memory_and_matches_unwrapped_output(
    pool: asyncpg.Pool, seed_conn: asyncpg.Connection
) -> None:
    # AC5
    student_id, session_id = await _seed_student_with_session(seed_conn, pool)
    agent_input = _make_input(student_id, session_id)

    unwrapped_outputs = []
    async for output in Aria().respond(agent_input):
        unwrapped_outputs.append(output)

    episodic_repo = EpisodicMemoryRepository(pool)
    wrapped = PersistentAgent(Aria(), episodic_repo)

    wrapped_outputs = []
    async for output in wrapped.stream(agent_input):
        wrapped_outputs.append(output)

    assert [o.response for o in wrapped_outputs] == [o.response for o in unwrapped_outputs]

    rows = await episodic_repo.recent_for_student(tenant_id="mcat", student_id=student_id)
    assert len(rows) == 1
    assert rows[0].summary == wrapped_outputs[-1].session_notes


async def test_quinn_persistent_agent_adjusts_ease_factor_on_correct_answer(
    pool: asyncpg.Pool, seed_conn: asyncpg.Connection
) -> None:
    # AC6
    student_id, session_id = await _seed_student_with_session(seed_conn, pool)
    episodic_repo = EpisodicMemoryRepository(pool)
    mastery_repo = ConceptMasteryRepository(pool)
    wrapped = QuinnPersistentAgent(Quinn(), episodic_repo, mastery_repo)

    # Turn 1: present a question (no DB effect on concept_mastery yet).
    fresh_input = _make_input(student_id, session_id)
    fresh_outputs = [o async for o in wrapped.stream(fresh_input)]
    assert len(fresh_outputs) == 1

    # Turn 2: answer correctly -- pending question comes from Quinn's own
    # session_notes marker, echoed back via episodic_context per its existing
    # design (changes/2026/07/15/quinn-agent/).
    pending_marker = fresh_outputs[0].session_notes

    answer_input = _make_input(
        student_id,
        session_id,
        message="true",
        episodic_context=[
            EpisodicMemory(id="mem-1", summary=pending_marker, occurredAt="2026-01-01T00:00:00Z", relevanceScore=1.0)
        ],
    )
    answer_outputs = [o async for o in wrapped.stream(answer_input)]
    assert len(answer_outputs) == 1

    # Verify via seed_conn (superuser, bypasses RLS) -- app_backend's own pool
    # has no tenant/acting-user context set on an ad-hoc acquire(), so a raw
    # query through it would be silently RLS-filtered to zero rows.
    row = await seed_conn.fetchrow(
        "select ease_factor, review_count from concept_mastery where student_id = $1", student_id
    )
    assert row is not None
    assert row["ease_factor"] > 2.5  # DEFAULT_EASE_FACTOR
    assert row["review_count"] == 1


async def test_quinn_persistent_agent_adjusts_ease_factor_on_incorrect_answer(
    pool: asyncpg.Pool, seed_conn: asyncpg.Connection
) -> None:
    # AC6
    student_id, session_id = await _seed_student_with_session(seed_conn, pool)
    episodic_repo = EpisodicMemoryRepository(pool)
    mastery_repo = ConceptMasteryRepository(pool)
    wrapped = QuinnPersistentAgent(Quinn(), episodic_repo, mastery_repo)

    fresh_input = _make_input(student_id, session_id)
    fresh_outputs = [o async for o in wrapped.stream(fresh_input)]

    pending_marker = fresh_outputs[0].session_notes

    answer_input = _make_input(
        student_id,
        session_id,
        message="false",
        episodic_context=[
            EpisodicMemory(id="mem-1", summary=pending_marker, occurredAt="2026-01-01T00:00:00Z", relevanceScore=1.0)
        ],
    )
    await anext_all(wrapped.stream(answer_input))

    row = await seed_conn.fetchrow(
        "select ease_factor from concept_mastery where student_id = $1", student_id
    )
    assert row is not None
    assert row["ease_factor"] < 2.5


async def anext_all(agen) -> None:
    async for _ in agen:
        pass
