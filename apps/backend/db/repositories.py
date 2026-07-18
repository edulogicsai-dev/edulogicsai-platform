"""
Repositories for core-data-schema's 7 tables. Every method routes through
tenant_scoped() -- no method accepts a raw connection or bypasses tenant
scoping. Every method operating on a specific student's row also passes
acting_user_id, since core-data-schema's RLS policies check
`auth.uid() = student_id`, which a backend connection has no other way to
satisfy -- see nexus.tenant_context's module docstring and SPEC.md
Gaps & Assumptions. See changes/2026/07/17/nexus-orchestration/
changes/database-wiring/SPEC.md FR2, FR6.
"""

import datetime

import asyncpg

from db.tenant_scope import tenant_scoped
from domains._contracts.agent_io import ContentChunk, EpisodicMemory, StudentProfile

DEFAULT_EASE_FACTOR = 2.5
MAX_EASE_FACTOR = 3.0
MIN_EASE_FACTOR = 1.3


class AgentSessionRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_session(self, tenant_id: str, student_id: str, agent_id: str) -> str:
        async with tenant_scoped(self._pool, tenant_id, acting_user_id=student_id) as conn:
            row = await conn.fetchrow(
                "insert into agent_sessions (tenant_id, student_id, agent_id) values ($1, $2, $3) returning id",
                tenant_id,
                student_id,
                agent_id,
            )
            return str(row["id"])

    async def increment_turn_count(self, session_id: str, tenant_id: str, student_id: str) -> None:
        # student_id added to the originally-sketched signature -- required
        # to satisfy the UPDATE policy's auth.uid() = student_id check.
        async with tenant_scoped(self._pool, tenant_id, acting_user_id=student_id) as conn:
            await conn.execute(
                "update agent_sessions set turn_count = turn_count + 1 where id = $1 and tenant_id = $2",
                session_id,
                tenant_id,
            )


class EpisodicMemoryRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def write(
        self,
        tenant_id: str,
        student_id: str,
        session_id: str,
        summary: str,
        relevance_score: float | None = None,
    ) -> None:
        async with tenant_scoped(self._pool, tenant_id, acting_user_id=student_id) as conn:
            await conn.execute(
                """
                insert into episodic_memory (tenant_id, student_id, session_id, summary, relevance_score)
                values ($1, $2, $3, $4, $5)
                """,
                tenant_id,
                student_id,
                session_id,
                summary,
                relevance_score,
            )

    async def recent_for_student(self, tenant_id: str, student_id: str, limit: int = 10) -> list[EpisodicMemory]:
        async with tenant_scoped(self._pool, tenant_id, acting_user_id=student_id) as conn:
            rows = await conn.fetch(
                """
                select id, summary, occurred_at, relevance_score
                from episodic_memory
                where student_id = $1
                order by occurred_at desc
                limit $2
                """,
                student_id,
                limit,
            )
            return [
                EpisodicMemory(
                    id=str(r["id"]),
                    summary=r["summary"],
                    occurredAt=r["occurred_at"].isoformat(),
                    relevanceScore=r["relevance_score"] if r["relevance_score"] is not None else 0.0,
                )
                for r in rows
            ]


class StudentProfileRepository:
    """
    Discovered during this change: the StudentProfile contract (userId,
    displayName, createdAt) predates core-data-schema's student_profiles
    table, which actually stores test_date/score_goal/current_score/
    study_streak -- there is no displayName column. displayName is sourced
    via a join to the existing Stripe-starter `users` table's full_name;
    the learning-state columns aren't exposed here since StudentProfile has
    no field for them. See SPEC.md Gaps & Assumptions / Open Questions.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def load_profile(self, tenant_id: str, user_id: str) -> StudentProfile:
        async with tenant_scoped(self._pool, tenant_id, acting_user_id=user_id) as conn:
            row = await conn.fetchrow(
                """
                select sp.user_id, sp.created_at, u.full_name
                from student_profiles sp
                left join users u on u.id = sp.user_id
                where sp.user_id = $1 and sp.tenant_id = $2
                """,
                user_id,
                tenant_id,
            )
            if row is None:
                raise ValueError(f"No student_profiles row for user_id={user_id} tenant_id={tenant_id}")
            return StudentProfile(
                userId=str(row["user_id"]),
                displayName=row["full_name"] or "Student",
                createdAt=row["created_at"].isoformat(),
            )


class DomainContentRepository:
    """
    search() uses Postgres full-text search (to_tsvector/plainto_tsquery),
    not real pgvector similarity -- no embedding model is available to embed
    the query text in this environment. See SPEC.md FR6.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def search(self, tenant_id: str, query_text: str, limit: int = 5) -> list[ContentChunk]:
        async with tenant_scoped(self._pool, tenant_id) as conn:
            rows = await conn.fetch(
                """
                select id, content, source_id
                from domain_content
                where tenant_id = $1
                  and to_tsvector('english', content) @@ plainto_tsquery('english', $2)
                limit $3
                """,
                tenant_id,
                query_text,
                limit,
            )
            return [
                ContentChunk(id=str(r["id"]), text=r["content"], sourceId=r["source_id"], score=1.0) for r in rows
            ]


class ConceptMasteryRepository:
    """
    Simplified SM-2-style ease_factor adjustment -- not real FSRS-5
    (stability/difficulty). See core-data-schema's concept-mastery SPEC.md
    for the original discrepancy this continues.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def record_attempt(
        self, tenant_id: str, student_id: str, concept_id: str, correct: bool
    ) -> tuple[float, float]:
        async with tenant_scoped(self._pool, tenant_id, acting_user_id=student_id) as conn:
            existing = await conn.fetchrow(
                "select ease_factor from concept_mastery where student_id = $1 and tenant_id = $2 and concept_id = $3",
                student_id,
                tenant_id,
                concept_id,
            )
            previous_ease = float(existing["ease_factor"]) if existing else DEFAULT_EASE_FACTOR
            if correct:
                new_ease = min(previous_ease + 0.1, MAX_EASE_FACTOR)
            else:
                new_ease = max(previous_ease - 0.2, MIN_EASE_FACTOR)
            next_review = datetime.date.today() + datetime.timedelta(days=round(new_ease))

            await conn.execute(
                """
                insert into concept_mastery
                    (student_id, tenant_id, concept_id, ease_factor, review_count, last_reviewed_at, next_review)
                values ($1, $2, $3, $4, 1, now(), $5)
                on conflict (student_id, tenant_id, concept_id) do update set
                    ease_factor = excluded.ease_factor,
                    review_count = concept_mastery.review_count + 1,
                    last_reviewed_at = excluded.last_reviewed_at,
                    next_review = excluded.next_review,
                    updated_at = now()
                """,
                student_id,
                tenant_id,
                concept_id,
                new_ease,
                next_review,
            )
            return (previous_ease, new_ease)
