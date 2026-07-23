import asyncpg


async def create_pool(dsn: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(
        dsn,
        statement_cache_size=0,
        min_size=1,
        max_size=5,
    )
