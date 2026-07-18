---
title: SSE Chat Endpoint - Implementation Plan
change: sse-endpoint
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-17
sdd_version: 7.3.0
---

## Overview

Implementation plan for: SSE Chat Endpoint

Specification: [SPEC.md](./SPEC.md)

## Affected Components

- apps/backend (existing, untracked as an SDD component)

## Prerequisites

- `langgraph-state-machine` — complete. Provides `run_turn`.
- `database-wiring` — complete. Provides live `AgentInput` assembly, `AgentSessionRepository`, `student_profiles` membership data.

## Implementation Phases

### Phase 1: JWT Verification

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [x] Add `PyJWT` to `apps/backend/pyproject.toml` dependencies
- [x] Create `apps/backend/auth/jwt_verifier.py`: `JWTVerifier` (FR2)

Deliverables:
- `JWTVerifier` implements FR2

### Phase 2: Chat Endpoint

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [x] Create `apps/backend/api/chat.py`: `ChatRequest` (FR1), tenant membership check (FR3), session resolution (FR4), SSE streaming (FR5), error handling (FR6)
- [x] Wire the router into `apps/backend/main.py` — conditionally, inside a `lifespan` handler gated on `JWT_SECRET`/`DATABASE_URL` being set, so the app still boots (and `test_health.py` still passes) without real credentials

Deliverables:
- `POST /api/chat` implements FR1–FR6

### Phase 3: Integration Tests

**Standards:** N/A (pytest)

Tasks:
- [x] Switched from FastAPI's `TestClient` to `httpx.AsyncClient` + `ASGITransport` after discovering `TestClient` runs the app in a separate thread/event loop, which broke the `asyncpg` pool created in the test's own event loop
- [x] `test_chat_endpoint.py`: valid end-to-end request (AC1)
- [x] `test_chat_endpoint.py`: malformed body → 422 (AC2)
- [x] `test_chat_endpoint.py`: missing/invalid JWT → 401 (AC3)
- [x] `test_chat_endpoint.py`: valid JWT, no tenant membership → 403 (AC4)
- [x] `test_chat_endpoint.py`: ARIA→MIRA handoff visible in stream (AC5) — uses a real `agent_sessions` row, not a fabricated session id (asyncpg rejected the first attempt: not a valid UUID)
- [x] `test_chat_endpoint.py`: forced mid-turn exception → graceful `event: error` (AC6) — first attempt (empty-agents domain config) didn't actually error, since LangGraph silently drops writes to an unmapped entry channel; switched to a raising agent factory instead
- [x] `test_chat_endpoint.py`: new vs. existing session_id behavior (AC7)

Deliverables:
- Full pytest suite passing (70/70 — 63 existing + 7 new), covering AC1–AC7

### Phase 4: Review

**Standards:** N/A (manual)

Tasks:
- [x] Spec compliance review against all 7 acceptance criteria — all satisfied
- [x] Confirm full existing test suite (all prior changes in this epic + all 3 agents) still passes unchanged — confirmed

## Expected Files

### Files to Create

| File | Component | Description |
|------|-----------|--------------|
| `apps/backend/auth/__init__.py` | apps/backend | Package init |
| `apps/backend/auth/jwt_verifier.py` | apps/backend | `JWTVerifier` |
| `apps/backend/api/__init__.py` | apps/backend | Package init |
| `apps/backend/api/chat.py` | apps/backend | `POST /api/chat` |
| `apps/backend/tests/test_chat_endpoint.py` | apps/backend | |

### Files to Modify

| File | Description |
|------|-------------|
| `apps/backend/main.py` | Mount the `/api/chat` router |
| `apps/backend/pyproject.toml` | Add `PyJWT` dependency |

## Implementation State

### Current Phase

- **Phase:** Complete (all 4 phases)
- **Status:** complete
- **Last Updated:** 2026-07-17

### Completed Phases

| Phase | Completed | Notes |
|-------|-----------|-------|
| 1 | [x] | |
| 2 | [x] | Switched `main.py` from deprecated `@app.on_event("startup")` to the `lifespan` context-manager pattern |
| 3 | [x] | Two real test-methodology fixes: TestClient→AsyncClient event-loop mismatch, and a properly-raising error-forcing fixture |
| 4 | [x] | |

### Actual Files Changed

| File | Action | Phase | Notes |
|------|--------|-------|-------|
| `apps/backend/auth/__init__.py` | Create | 1 | |
| `apps/backend/auth/jwt_verifier.py` | Create | 1 | |
| `apps/backend/api/__init__.py` | Create | 2 | |
| `apps/backend/api/chat.py` | Create | 2 | |
| `apps/backend/main.py` | Modify | 2 | Conditional `/api/chat` mount via `lifespan` |
| `apps/backend/tests/test_chat_endpoint.py` | Create | 3 | |
| `apps/backend/pyproject.toml` | Modify | 1 | Added `PyJWT` |

### Blockers

- (none)

## Dependencies

- `langgraph-state-machine`, `database-wiring`.

## Risks

| Risk | Mitigation |
|------|------------|
| FR3's tenant-membership check wasn't in the original request — discovered as a real gap during spec drafting | Now a first-class FR/AC, not an afterthought |
| Test JWT secret differs from real Supabase signing key | `JWTVerifier` takes the secret as a constructor parameter — swapping in the real key later is config, not code |
