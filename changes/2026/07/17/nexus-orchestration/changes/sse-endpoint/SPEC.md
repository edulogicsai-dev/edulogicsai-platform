---
title: SSE Chat Endpoint
type: feature
status: active
domain: mcat
issue: TBD
created: 2026-07-17
updated: 2026-07-17
sdd_version: 7.3.0
parent_epic: ../../SPEC.md
affected_components: []
---

## Overview

`POST /api/chat` — the endpoint students actually hit. Validates a Supabase JWT, resolves/creates the session, runs a turn through the LangGraph state machine with live database-backed context, and streams the result as Server-Sent Events, with agent handoffs visible as the `agent_id` changes across events.

### Background

Every piece this endpoint composes already exists: `run_turn` (`langgraph-state-machine`) executes the handoff cascade; live `AgentInput` assembly (`database-wiring`) pulls real context. Nothing yet exposes this over HTTP.

### Current State

`apps/backend/main.py` has only `GET /health`.

---

## Functional Requirements

### FR1: Request Contract

**Behavior:**
- `POST /api/chat` accepts a JSON body: `ChatRequest(message: str, session_id: Optional[str] = None, tenant_id: str)` (Pydantic model — FastAPI returns `422` automatically on validation failure, e.g. missing `message`/`tenant_id`).

### FR2: JWT Authentication

**Behavior:**
- The `Authorization: Bearer <token>` header shall be verified against a configured secret (`JWTVerifier`, secret from an environment variable — **a test secret in this change**, not Supabase's real signing key, per the epic's local-substitute decision).
- On success, the token's `sub` claim is the authenticated `user_id`.
- On missing, malformed, or invalid-signature/expired token: `401`.

### FR3: Tenant Membership Validation (Security Gap Closed Here)

**Behavior:**
- Before processing, the endpoint shall confirm the authenticated `user_id` actually has a `student_profiles` row for the request's `tenant_id` — **discovered during this change**: without this check, a client could supply *any* `tenant_id` in the request body, and since tenant context is set from that same client-supplied value, a validated-but-wrong-tenant request would otherwise pass straight through to `SET LOCAL app.tenant_id` with no verification the user actually belongs to that tenant. `student_profiles`' existing `(user_id, tenant_id)` composite key is exactly the membership record needed — no new table required.
- On no matching `student_profiles` row: `403`.

### FR4: Session Resolution

**Behavior:**
- If `session_id` is omitted: create a new `agent_sessions` row (`AgentSessionRepository.create_session`) with the domain's classified/default entry agent.
- If `session_id` is provided: verify it belongs to `(user_id, tenant_id)`, then `increment_turn_count`.

### FR5: SSE Streaming

**Behavior:**
- Response `Content-Type: text/event-stream`.
- Runs the turn via `langgraph-state-machine`'s `run_turn`, using `database-wiring`'s live `AgentInput` assembly.
- Streams one `event: message` per `AgentOutput` produced this turn, in order — since `run_turn` already returns the full ordered cascade (ARIA→MIRA, etc.), streaming each in sequence makes handoffs visible as `agent_id` changes between consecutive events.
- Ends with a terminal `event: done` (empty data) once all outputs are streamed.

**Constraints:**
- **This is not yet token-level incremental generation** — since no agent currently calls a real LLM (all deterministic), "streaming" here means one SSE event per agent hop in the handoff cascade, not per-token. Real token streaming requires real LLM integration (out of scope — see Gaps & Assumptions).

### FR6: Error Handling

**Behavior:**
- Malformed request body → `422` (FastAPI/Pydantic, automatic).
- Auth failure → `401` (FR2).
- Tenant-membership failure → `403` (FR3).
- Any exception raised during turn execution (after the stream has started) → a graceful `event: error` SSE event with a safe (non-internal-detail-leaking) message — not a raw `500` or a silently dropped connection.

## Acceptance Criteria

- [ ] **AC1:** Given a valid request, valid JWT, and valid tenant membership, when `POST /api/chat` is called, then the response streams at least one `event: message` and ends with `event: done`.
- [ ] **AC2:** Given a request body missing `message`, when `POST /api/chat` is called, then it returns `422` and no stream starts.
- [ ] **AC3:** Given a missing or invalid JWT, when `POST /api/chat` is called, then it returns `401`.
- [ ] **AC4:** Given a valid JWT for a user with no `student_profiles` row for the requested `tenant_id`, when `POST /api/chat` is called, then it returns `403`.
- [ ] **AC5:** Given input that triggers ARIA's frustration handoff (same fixture as `langgraph-state-machine`'s AC2), when `POST /api/chat` is called, then the stream contains 2 `event: message` events with `agent_id` `'aria'` then `'mira'`, in order.
- [ ] **AC6:** Given a turn execution that raises (simulated via a repository configured to fail), when `POST /api/chat` is called, then the stream emits `event: error` instead of a raw `500` or a dropped connection.
- [ ] **AC7:** Given no `session_id` in the request, when `POST /api/chat` is called, then a new `agent_sessions` row is created; given a valid existing `session_id`, then `turn_count` increments and no duplicate session is created.

## Technical Design

### Architecture

```
apps/backend/
├── auth/
│   └── jwt_verifier.py     # JWTVerifier, verify(token) -> user_id | raises
├── api/
│   └── chat.py             # POST /api/chat: ChatRequest, endpoint, SSE formatting
└── main.py                 # mounts the /api/chat router (modified)
```

### SSE Event Format

```
event: message
data: {"agent_id": "aria", "response": "...", "cited_chunks": [...], "risk_level": "low", ...}

event: message
data: {"agent_id": "mira", "response": "...", ...}

event: done
data:
```

Error case:

```
event: error
data: {"error": "Something went wrong processing your message."}
```

## Gaps & Assumptions

- "Streaming" is per-agent-hop (one SSE event per cascade step), not per-token — real token-level streaming needs a live LLM integration, which doesn't exist yet (all 3 agents are deterministic). Flagged, not hidden.
- The JWT secret used for verification in this change is a test secret, not Supabase's real signing key (epic Requirements Discovery) — swapping in the real key when credentials exist should be a config change, not a code change, since `JWTVerifier` takes the secret as a parameter.
- `main.py`'s `/api/chat` mounting is conditional on `JWT_SECRET`/`DATABASE_URL` being set (checked in a `lifespan` handler) — neither exists in this environment, so the router simply isn't mounted for `apps/backend`'s default/test usage, rather than crashing every other test that boots the app (e.g. `test_health.py`).
- **Discovered during implementation:** FastAPI's synchronous `TestClient` runs the ASGI app in a separate thread with its own event loop — an `asyncpg` pool created in the test's own (pytest-asyncio) event loop can't be used from that other loop (`InterfaceError: another operation is in progress`). Switched to `httpx.AsyncClient` + `ASGITransport`, which calls the app in-process on the same loop. This matters for anyone writing further async-DB-backed FastAPI tests in this codebase, not just this change.
- **Discovered during implementation:** an empty-agents `DomainConfig` doesn't make `run_turn` raise — LangGraph's conditional entry-point routing silently drops a write to an unmapped channel (logs a warning, produces zero outputs) rather than erroring. AC6's test forces a real error via an agent factory that raises inside a genuine graph node instead.

## Testing Strategy

### Integration Tests (`httpx.AsyncClient` + `ASGITransport`, local Postgres, test JWT secret)

| Test Case | Expected Behavior |
|-----------|--------------------|
| Valid request end-to-end | Streams messages, ends with `done` (AC1) |
| Missing `message` field | `422` (AC2) |
| Missing/invalid JWT | `401` (AC3) |
| Valid JWT, no `student_profiles` row for tenant | `403` (AC4) |
| ARIA→MIRA handoff input (real `agent_sessions` row, not a fabricated session id) | 2 ordered `event: message`, correct `agent_id`s (AC5) |
| Forced exception via a raising agent factory | `event: error`, not a crash (AC6) |
| No `session_id` vs. existing `session_id` | New session created vs. `turn_count` incremented, no duplicate (AC7) |

## Dependencies

### Internal Dependencies

| Component | Reason |
|-----------|--------|
| `langgraph-state-machine` | `run_turn` |
| `database-wiring` | Live `AgentInput` assembly, `AgentSessionRepository` |

### External Dependencies

| Library | Reason |
|---------|--------|
| `PyJWT` | JWT verification |

## Out of Scope

- Real Supabase JWT signing key.
- Token-level incremental streaming (needs real LLM integration).
- Rate limiting, CORS configuration, production auth hardening beyond the membership check in FR3.
- Frontend (`apps/web`) integration.

## References

- `changes/2026/07/17/nexus-orchestration/SPEC.md` — parent epic
- `changes/2026/07/17/nexus-orchestration/changes/langgraph-state-machine/SPEC.md` — `run_turn`
- `changes/2026/07/17/nexus-orchestration/changes/database-wiring/SPEC.md` — live `AgentInput` assembly, `student_profiles` membership data
