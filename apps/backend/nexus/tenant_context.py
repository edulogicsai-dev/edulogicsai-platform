"""
Tenant-context helper matching core-data-schema's current_tenant() RLS
mechanism exactly (changes/2026/07/16/core-data-schema/changes/tenant-foundation/).
`conn` is a minimal Protocol so this is testable with a mock connection here;
database-wiring exercises it against a real (local) connection.

Uses set_config(), not "SET LOCAL ... = $1" -- SET/SET LOCAL do not support
bind parameters in Postgres (this would raise a syntax error at execution
time, not just a style choice). set_config(setting, value, is_local) is a
regular function call, so it supports parameter binding; is_local=true gives
the same transaction-scoped behavior as SET LOCAL, which is what
current_tenant()'s current_setting('app.tenant_id', true) call expects.

set_acting_user() exists because of a real gap discovered while wiring
database-wiring: core-data-schema's RLS policies check
`auth.uid() = student_id AND tenant_id = current_tenant()`. auth.uid() reads
the `request.jwt.claim.sub` GUC, which PostgREST populates automatically for
client-originated requests -- but a raw backend connection has no JWT at
all, so auth.uid() would resolve to NULL and every policy would deny.
set_acting_user() sets that same GUC directly so the backend can act "as" the
student it's processing a turn for, without inventing a second, parallel set
of RLS policies just for backend access. See
changes/2026/07/17/nexus-orchestration/changes/database-wiring/SPEC.md
Gaps & Assumptions.
"""

from typing import Protocol


class TenantScopedConnection(Protocol):
    async def execute(self, query: str, *args: object) -> object: ...


async def set_tenant_context(conn: TenantScopedConnection, tenant_id: str) -> None:
    await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)


async def set_acting_user(conn: TenantScopedConnection, user_id: str) -> None:
    await conn.execute("SELECT set_config('request.jwt.claim.sub', $1, true)", user_id)
