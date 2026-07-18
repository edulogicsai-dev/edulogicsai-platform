import os
import uuid

import asyncpg
import pytest

from db.live_agent_input import append_to_session_history, build_live_agent_input
from db.repositories import DomainContentRepository, EpisodicMemoryRepository, StudentProfileRepository
from domains._contracts.agent_io import Message

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


async def test_build_live_agent_input_composes_real_data(pool: asyncpg.Pool, seed_conn: asyncpg.Connection) -> None:
    student_id = str(uuid.uuid4())
    await seed_conn.execute("insert into auth.users (id) values ($1)", student_id)
    await seed_conn.execute("insert into student_profiles (user_id, tenant_id) values ($1, 'mcat')", student_id)
    await seed_conn.execute(
        "insert into domain_content (tenant_id, source_id, content) values ('mcat', 'enzyme_kinetics_01', $1)",
        "Enzymes lower the activation energy of biochemical reactions.",
    )

    session_id = "session-live-input-test"
    append_to_session_history(
        session_id, Message(role="user", content="hi", timestamp="2026-01-01T00:00:00Z")
    )

    student_profile_repo = StudentProfileRepository(pool)
    episodic_repo = EpisodicMemoryRepository(pool)
    content_repo = DomainContentRepository(pool)

    # plainto_tsquery ANDs every term -- a full natural-language question
    # ("Tell me about...") won't match a single-topic sentence via this
    # naive fallback (see DomainContentRepository's docstring: this is
    # explicitly not real semantic search). Using a query matching the
    # fallback's actual capability.
    agent_input = await build_live_agent_input(
        tenant_id="mcat",
        student_id=student_id,
        session_id=session_id,
        message="activation energy",
        student_profile_repo=student_profile_repo,
        episodic_repo=episodic_repo,
        content_repo=content_repo,
    )

    assert agent_input.student_profile.userId == student_id
    assert len(agent_input.session_history) == 1
    assert agent_input.retrieved_chunks[0].sourceId == "enzyme_kinetics_01"
    assert agent_input.episodic_context == []
