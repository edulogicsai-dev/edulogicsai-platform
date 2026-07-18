"""
Connection pool -- DSN read from an environment variable, never hardcoded.
See changes/2026/07/17/nexus-orchestration/changes/database-wiring/SPEC.md FR1.
"""

import asyncpg


async def create_pool(dsn: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn)
