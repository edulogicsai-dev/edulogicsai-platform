import json
import os
import uuid

import asyncpg
import httpx
import jwt
import pytest
from fastapi import FastAPI

import domains.mcat.domain_config  # noqa: F401 -- self-registration
from api.chat import create_chat_router
from auth.jwt_verifier import JWTVerifier
from domains._contracts.domain_registry import registry
from nexus.graph_builder import build_graph

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://app_backend@localhost/edulogicsai_nexus_test"
)
SEED_DATABASE_URL = os.environ.get("SEED_DATABASE_URL", "postgresql:///edulogicsai_nexus_test")
TEST_JWT_SECRET = "test-secret-not-the-real-supabase-key"

pytestmark = pytest.mark.asyncio

# Using httpx.AsyncClient + ASGITransport, not FastAPI's TestClient: TestClient
# runs the ASGI app in a separate thread with its own event loop, which broke
# the asyncpg pool created in the test's own event loop ("another operation
# is in progress") -- discovered while writing these tests. AsyncClient calls
# the app in-process on the same loop, avoiding the mismatch entirely.


def _make_token(user_id: str, secret: str = TEST_JWT_SECRET) -> str:
    return jwt.encode({"sub": user_id}, secret, algorithm="HS256")


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


@pytest.fixture
def client(pool: asyncpg.Pool) -> httpx.AsyncClient:
    app = FastAPI()
    domain_result = registry.resolve_domain("mcat")
    graph = build_graph(domain_result.config, registry)
    router = create_chat_router(
        jwt_verifier=JWTVerifier(secret=TEST_JWT_SECRET),
        pool=pool,
        graph=graph,
        default_entry_agent_id="aria",
    )
    app.include_router(router)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _seed_member(seed_conn: asyncpg.Connection, tenant_id: str = "mcat") -> str:
    user_id = str(uuid.uuid4())
    await seed_conn.execute("insert into auth.users (id) values ($1)", user_id)
    await seed_conn.execute(
        "insert into student_profiles (user_id, tenant_id) values ($1, $2)", user_id, tenant_id
    )
    return user_id


def _parse_sse_events(body: str) -> list[tuple[str, str]]:
    events = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        event_type = None
        data = None
        for line in block.splitlines():
            if line.startswith("event:"):
                event_type = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data = line[len("data:") :].strip()
        if event_type is not None:
            events.append((event_type, data or ""))
    return events


async def test_valid_request_streams_message_and_done(
    client: httpx.AsyncClient, seed_conn: asyncpg.Connection, mock_llm_transport
) -> None:
    # AC1
    user_id = await _seed_member(seed_conn)
    token = _make_token(user_id)

    async with client:
        response = await client.post(
            "/api/chat",
            json={"message": "Can you explain enzyme kinetics?", "tenant_id": "mcat"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    message_events = [e for e in events if e[0] == "message"]
    assert len(message_events) >= 1
    assert events[-1][0] == "done"


async def test_malformed_body_returns_422(client: httpx.AsyncClient, seed_conn: asyncpg.Connection) -> None:
    # AC2
    user_id = await _seed_member(seed_conn)
    token = _make_token(user_id)

    async with client:
        response = await client.post(
            "/api/chat",
            json={"tenant_id": "mcat"},  # missing "message"
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 422


async def test_missing_or_invalid_jwt_returns_401(client: httpx.AsyncClient) -> None:
    # AC3
    async with client:
        no_auth = await client.post("/api/chat", json={"message": "hi", "tenant_id": "mcat"})
        assert no_auth.status_code == 401

        bad_token = await client.post(
            "/api/chat",
            json={"message": "hi", "tenant_id": "mcat"},
            headers={"Authorization": "Bearer not-a-real-token"},
        )
    assert bad_token.status_code == 401


async def test_valid_jwt_without_tenant_membership_returns_403(client: httpx.AsyncClient) -> None:
    # AC4 -- valid token, but no student_profiles row for this user at all
    token = _make_token(str(uuid.uuid4()))

    async with client:
        response = await client.post(
            "/api/chat",
            json={"message": "hi", "tenant_id": "mcat"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 403


async def test_handoff_visible_across_ordered_sse_events(
    client: httpx.AsyncClient, seed_conn: asyncpg.Connection, mock_llm_transport
) -> None:
    # AC5
    user_id = await _seed_member(seed_conn)
    token = _make_token(user_id)

    # session_id must be a real agent_sessions row (UUID) for increment_turn_count
    # to succeed -- create one directly rather than fabricating a string id.
    session_row = await seed_conn.fetchrow(
        "insert into agent_sessions (tenant_id, student_id, agent_id) values ('mcat', $1, 'aria') returning id",
        user_id,
    )
    session_id = str(session_row["id"])

    # A single HTTP call's session_history comes from the in-process cache
    # (FR5), so seed it directly the way multiple real turns would build it up.
    from db.live_agent_input import append_to_session_history
    from domains._contracts.agent_io import Message

    for content in ["I don't get it at all", "This is so frustrating", "I give up, I'm lost"]:
        append_to_session_history(session_id, Message(role="user", content=content, timestamp="2026-01-01T00:00:00Z"))

    async with client:
        response = await client.post(
            "/api/chat",
            json={"message": "still stuck", "session_id": session_id, "tenant_id": "mcat"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    message_events = [json.loads(data) for etype, data in events if etype == "message"]
    agent_ids = [m["agent_id"] for m in message_events]
    assert agent_ids == ["aria", "mira"]


async def test_forced_turn_error_yields_graceful_sse_error_event(
    pool: asyncpg.Pool, seed_conn: asyncpg.Connection
) -> None:
    # AC6 -- force a deterministic error via an agent factory that raises
    # (an empty-agents domain config was tried first and turned out not to
    # error at all -- LangGraph silently drops writes to an unmapped entry
    # channel rather than raising -- so this forces the failure explicitly
    # inside a real graph node instead).
    from domains._contracts.domain_config import AgentDef, DomainConfig, EvalRubric
    from domains._contracts.domain_registry import DomainRegistry

    user_id = await _seed_member(seed_conn)
    token = _make_token(user_id)

    def _broken_agent_factory():
        raise RuntimeError("simulated agent construction failure")

    broken_registry = DomainRegistry()
    broken_config = DomainConfig(
        id="mcat",
        name="MCATai",
        subdomain="app.mcatai.test",
        agents=[AgentDef(id="aria", display_name="ARIA", create_agent=_broken_agent_factory)],
        content_index="mcat_content",
        eval_rubric=EvalRubric(criteria=[]),
        theme={},
        escalation_rules=[],
    )
    broken_registry.register(broken_config)
    broken_graph = build_graph(broken_config, broken_registry)

    app = FastAPI()
    router = create_chat_router(
        jwt_verifier=JWTVerifier(secret=TEST_JWT_SECRET),
        pool=pool,
        graph=broken_graph,
        default_entry_agent_id="aria",
    )
    app.include_router(router)
    broken_client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

    async with broken_client:
        response = await broken_client.post(
            "/api/chat",
            json={"message": "hello", "tenant_id": "mcat"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200  # stream already started
    events = _parse_sse_events(response.text)
    assert events[0][0] == "error"
    error_payload = json.loads(events[0][1])
    assert "error" in error_payload


async def test_new_session_created_vs_existing_session_incremented(
    client: httpx.AsyncClient, seed_conn: asyncpg.Connection, mock_llm_transport
) -> None:
    # AC7
    user_id = await _seed_member(seed_conn)
    token = _make_token(user_id)

    async with client:
        response = await client.post(
            "/api/chat",
            json={"message": "hello", "tenant_id": "mcat"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        row = await seed_conn.fetchrow(
            "select id, turn_count from agent_sessions where student_id = $1", user_id
        )
        assert row is not None
        session_id = str(row["id"])
        assert row["turn_count"] == 0

        response2 = await client.post(
            "/api/chat",
            json={"message": "another message", "session_id": session_id, "tenant_id": "mcat"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response2.status_code == 200

    updated_row = await seed_conn.fetchrow("select turn_count from agent_sessions where id = $1", row["id"])
    assert updated_row["turn_count"] == 1

    count_row = await seed_conn.fetchrow(
        "select count(*) as c from agent_sessions where student_id = $1", user_id
    )
    assert count_row["c"] == 1  # no duplicate session created
