---
title: NEXUS Orchestration Layer - Implementation Plan
change: nexus-orchestration
type: epic
spec: ./SPEC.md
status: draft
created: 2026-07-17
sdd_version: 7.3.0
---

## Overview

Implementation plan for epic: NEXUS Orchestration Layer

Specification: [SPEC.md](./SPEC.md)

## Change Order

| # | Change | Description | Dependencies | Status |
|---|--------|-------------|--------------|--------|
| 1 | [litellm-gateway](./changes/litellm-gateway/PLAN.md) | LiteLLM config, model routing, caching, health check | None | complete |
| 2 | [nexus-supervisor](./changes/nexus-supervisor/PLAN.md) | Python DomainConfig mirror, MCAT registration, intent classification | litellm-gateway | complete |
| 3 | [langgraph-state-machine](./changes/langgraph-state-machine/PLAN.md) | Dynamic graph, handoff edges, checkpointing, HITL | nexus-supervisor | complete |
| 4 | [database-wiring](./changes/database-wiring/PLAN.md) | Real DB reads/writes for all 3 agents | nexus-supervisor | complete |
| 5 | [sse-endpoint](./changes/sse-endpoint/PLAN.md) | POST /api/chat, JWT auth, SSE streaming | langgraph-state-machine, database-wiring | complete |

## Dependency Graph

```
litellm-gateway
    └──► nexus-supervisor
              ├──► langgraph-state-machine ──┐
              └──► database-wiring ──────────┴──► sse-endpoint
```

`langgraph-state-machine` and `database-wiring` both depend only on `nexus-supervisor` and could be built in parallel — this plan implements them in the numbered order for a simpler linear PR sequence, matching the user-specified dependency order.

## PR Strategy

One PR per child change. Branch naming: `epic/nexus-orchestration/<change-name>`.

## Verification Approach

No Supabase CLI, Docker, or real Anthropic/Supabase credentials are available in this environment (same constraint discovered during `core-data-schema`, now extended to LLM/auth). Per explicit decision:
- `database-wiring` reuses the local Postgres 17 + pgvector 0.8.5 instance approach from `core-data-schema`, reapplying its 7 migrations.
- LLM-backed logic (intent classification) sits behind protocols with deterministic test implementations, mirroring ARIA's `FrustrationEstimator` pattern — the real LiteLLM-backed implementation is written but not exercised against a live API key.
- JWT validation is tested against a locally-generated test secret/token, not Supabase's real signing key.

## Progress Tracking

- [x] Change 1: litellm-gateway
- [x] Change 2: nexus-supervisor
- [x] Change 3: langgraph-state-machine
- [x] Change 4: database-wiring
- [x] Change 5: sse-endpoint

## Verification Summary

All 5 children verified for real, not just reviewed — 70/70 backend tests passing (32 pre-epic + 38 new), against a real local Postgres 17 + pgvector 0.8.5 instance and real LangGraph 1.2.9. Notable discoveries surfaced and fixed during implementation, not glossed over:

- **`nexus-supervisor`**: the originally-sketched `SET LOCAL app.tenant_id = $1` is invalid Postgres syntax (no bind-parameter support) — fixed via `set_config()`. A grep-audit test caught real domain-specific leakage in a code *comment*.
- **`langgraph-state-machine`**: needed zero credentials at all, since all 3 agents are deterministic — the full ARIA→MIRA handoff cascade, including "no cold starts," was exercised against the real agents, not mocks.
- **`database-wiring`** (the most gap-dense child): `auth.uid() = student_id` RLS policies don't resolve for backend-originated writes (no JWT context) — resolved via a new `set_acting_user()` helper rather than inventing parallel RLS policies. `StudentProfile`'s contract shape doesn't match `student_profiles`' actual columns. `concept_mastery`'s domain-prefix constraint didn't match QUINN's (never-prefixed) internal concept tracking. The default local Postgres role is a superuser and silently bypasses RLS — a dedicated non-superuser role was required for every RLS assertion to mean anything.
- **`sse-endpoint`**: FastAPI's synchronous `TestClient` runs the app in a separate thread/event loop, incompatible with an `asyncpg` pool created in the test's own loop — switched to `httpx.AsyncClient` + `ASGITransport`. An "empty agents" domain config meant to force an error instead revealed that LangGraph silently drops writes to unmapped channels rather than raising.
- Epic AC3 (Stripe starter tables untouched) confirmed via `git status` at completion — zero diff.
- Local Postgres server, test database, and the `app_backend` test role were all torn down after verification; nothing persists in this environment as a side effect.

## Resource Usage

| Change | Tokens (Input) | Tokens (Output) | Turns | Duration | Notes |
|--------|----------------|------------------|-------|----------|-------|
| litellm-gateway | - | - | - | | |
| nexus-supervisor | - | - | - | | |
| langgraph-state-machine | - | - | - | | |
| database-wiring | - | - | - | | |
| sse-endpoint | - | - | - | | |
| **Total** | **-** | **-** | **-** | **-** | |
