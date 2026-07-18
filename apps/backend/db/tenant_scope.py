"""
Every query in database-wiring goes through this, so RLS is enforced
identically for every repository method. See
changes/2026/07/17/nexus-orchestration/changes/database-wiring/SPEC.md FR1.

Accepts an optional acting_user_id: core-data-schema's RLS policies check
`auth.uid() = student_id`, which only resolves for client-originated (JWT)
requests. For backend-originated writes on behalf of a specific student,
pass that student's id so the connection "acts as" them for this scoped
transaction -- see nexus.tenant_context's module docstring for the full
discovery.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import asyncpg

from nexus.tenant_context import set_acting_user, set_tenant_context


@asynccontextmanager
async def tenant_scoped(
    pool: asyncpg.Pool, tenant_id: str, acting_user_id: Optional[str] = None
) -> AsyncIterator[asyncpg.Connection]:
    async with pool.acquire() as conn:
        async with conn.transaction():
            await set_tenant_context(conn, tenant_id)
            if acting_user_id is not None:
                await set_acting_user(conn, acting_user_id)
            yield conn
