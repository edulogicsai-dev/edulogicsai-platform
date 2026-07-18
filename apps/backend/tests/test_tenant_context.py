import pytest

from nexus.tenant_context import set_tenant_context


class _MockConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def execute(self, query: str, *args: object) -> None:
        self.calls.append((query, args))


@pytest.mark.asyncio
async def test_set_tenant_context_issues_set_config_with_correct_args() -> None:
    # AC7
    conn = _MockConnection()
    await set_tenant_context(conn, "mcat")
    assert len(conn.calls) == 1
    query, args = conn.calls[0]
    assert query == "SELECT set_config('app.tenant_id', $1, true)"
    assert args == ("mcat",)
