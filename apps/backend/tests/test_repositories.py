"""
Integration tests against a real local Postgres instance (Postgres 17 +
pgvector 0.8.5, core-data-schema's 7 migrations applied, stub auth schema) --
see changes/2026/07/17/nexus-orchestration/changes/database-wiring/SPEC.md
Testing Strategy.

Two roles are used deliberately:
- SEED_DATABASE_URL (superuser): bypasses RLS, used only to set up test
  preconditions (inserting auth.users rows, etc.) -- the table owner/
  superuser bypasses RLS by default, so using it for the repositories under
  test would make every RLS assertion meaningless (same lesson learned in
  core-data-schema's own tests).
- TEST_DATABASE_URL (app_backend, non-superuser): what the repositories
  under test actually connect as, so RLS is genuinely exercised.
"""

import os
import uuid

import asyncpg
import pytest

from db.repositories import (
    AgentSessionRepository,
    ConceptMasteryRepository,
    DomainContentRepository,
    EpisodicMemoryRepository,
    StudentProfileRepository,
)
from db.tenant_scope import tenant_scoped

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


async def _seed_user_and_profile(seed_conn: asyncpg.Connection, tenant_id: str = "mcat") -> str:
    user_id = str(uuid.uuid4())
    await seed_conn.execute("insert into auth.users (id) values ($1)", user_id)
    await seed_conn.execute(
        "insert into student_profiles (user_id, tenant_id) values ($1, $2)", user_id, tenant_id
    )
    return user_id


async def test_create_session_and_increment_turn_count(pool: asyncpg.Pool, seed_conn: asyncpg.Connection) -> None:
    # AC1
    student_id = await _seed_user_and_profile(seed_conn)
    repo = AgentSessionRepository(pool)

    session_id = await repo.create_session(tenant_id="mcat", student_id=student_id, agent_id="aria")
    await repo.increment_turn_count(session_id=session_id, tenant_id="mcat", student_id=student_id)
    await repo.increment_turn_count(session_id=session_id, tenant_id="mcat", student_id=student_id)

    row = await seed_conn.fetchrow("select turn_count from agent_sessions where id = $1", uuid.UUID(session_id))
    assert row["turn_count"] == 2


async def test_episodic_memory_round_trips_and_is_tenant_isolated(
    pool: asyncpg.Pool, seed_conn: asyncpg.Connection
) -> None:
    # AC2
    student_id = await _seed_user_and_profile(seed_conn)
    session_repo = AgentSessionRepository(pool)
    session_id = await session_repo.create_session(tenant_id="mcat", student_id=student_id, agent_id="aria")

    episodic_repo = EpisodicMemoryRepository(pool)
    await episodic_repo.write(
        tenant_id="mcat", student_id=student_id, session_id=session_id, summary="discussed enzyme kinetics"
    )

    results = await episodic_repo.recent_for_student(tenant_id="mcat", student_id=student_id)
    assert len(results) == 1
    assert results[0].summary == "discussed enzyme kinetics"

    await seed_conn.execute(
        "insert into tenants (id, name, subdomain) values ('gre', 'GREai', 'app.greai.test') on conflict do nothing"
    )
    other_tenant_results = await episodic_repo.recent_for_student(tenant_id="gre", student_id=student_id)
    assert other_tenant_results == []


async def test_load_profile_returns_matching_student_profile(
    pool: asyncpg.Pool, seed_conn: asyncpg.Connection
) -> None:
    # AC3
    student_id = await _seed_user_and_profile(seed_conn)
    # The starter's handle_new_user() trigger already inserted a `users` row
    # when auth.users got the insert above -- update it rather than insert.
    await seed_conn.execute("update users set full_name = $2 where id = $1", student_id, "Alex Rivera")

    repo = StudentProfileRepository(pool)
    profile = await repo.load_profile(tenant_id="mcat", user_id=student_id)

    assert profile.userId == student_id
    assert profile.displayName == "Alex Rivera"


async def test_domain_content_search_returns_matching_chunk(
    pool: asyncpg.Pool, seed_conn: asyncpg.Connection
) -> None:
    # AC4
    await seed_conn.execute(
        "insert into domain_content (tenant_id, source_id, content) values ('mcat', 'enzyme_kinetics_01', $1)",
        "Enzymes lower the activation energy of biochemical reactions.",
    )

    repo = DomainContentRepository(pool)
    results = await repo.search(tenant_id="mcat", query_text="activation energy")

    assert len(results) >= 1
    assert results[0].sourceId == "enzyme_kinetics_01"


async def test_concept_mastery_repository_cross_tenant_isolation(
    pool: asyncpg.Pool, seed_conn: asyncpg.Connection
) -> None:
    # AC7 -- exercises RLS itself: query for the mcat-tenant row while scoped
    # to a different tenant, with no explicit tenant_id filter in the query,
    # and confirm RLS still hides it.
    student_id = await _seed_user_and_profile(seed_conn, tenant_id="mcat")
    await seed_conn.execute(
        "insert into tenants (id, name, subdomain) values ('gre', 'GREai', 'app.greai.test') on conflict do nothing"
    )
    repo = ConceptMasteryRepository(pool)
    await repo.record_attempt(tenant_id="mcat", student_id=student_id, concept_id="mcat::enzyme_kinetics", correct=True)

    async with tenant_scoped(pool, "gre", acting_user_id=student_id) as conn:
        rows_visible_under_gre = await conn.fetch(
            "select * from concept_mastery where student_id = $1", student_id
        )
    assert rows_visible_under_gre == []

    async with tenant_scoped(pool, "mcat", acting_user_id=student_id) as conn:
        rows_visible_under_mcat = await conn.fetch(
            "select * from concept_mastery where student_id = $1", student_id
        )
    assert len(rows_visible_under_mcat) == 1
