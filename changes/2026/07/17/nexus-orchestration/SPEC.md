---
title: NEXUS Orchestration Layer
type: epic
status: active
domain: mcat
issue: TBD
created: 2026-07-17
updated: 2026-07-17
sdd_version: 7.3.0
affected_components: []
---

## Overview

Connect ARIA, MIRA, and QUINN — currently tested only in isolation with fixture data (`changes/2026/07/10/aria-agent/`, `changes/2026/07/15/mira-agent/`, `changes/2026/07/15/quinn-agent/`) — to a live HTTP endpoint students can actually use. This is the layer CLAUDE.md describes as NEXUS: "domain-agnostic supervisor agent... reads DomainConfig.agents at boot... contains zero domain-specific logic," backed by LiteLLM routing and LangGraph state management, all on `apps/backend` (Python/FastAPI).

### Background

Three agents exist and are fully unit-tested (32 tests passing as of `changes/2026/07/15/quinn-agent/`), and a complete multi-tenant database schema exists and is verified (`changes/2026/07/16/core-data-schema/`, 7 tables, 39 ACs). Neither is connected to the other, and neither is reachable over HTTP. This epic is the wiring: real LLM routing, a real supervisor that loads the agent roster instead of hardcoding it, real state transitions on handoff, real database reads/writes replacing the `session_notes`/`episodic_context` heuristics, and a real streaming endpoint.

### Current State

- `apps/backend` has a bare FastAPI scaffold (`GET /health` only) plus ARIA/MIRA/QUINN as directly-instantiable Python classes — nothing serves them over HTTP.
- `DomainConfig`/`DomainRegistry` exist only in TypeScript (`packages/core`); no Python equivalent, and no actual `domains/mcat` config registering the 3 built agents exists yet — explicitly deferred as an open question on all three agents' specs.
- No LiteLLM, no LangGraph, no database client wiring, no JWT/auth anywhere in `apps/backend`.
- No real credentials for Anthropic, Supabase `service_role`, or Supabase Auth JWT signing are available in this environment (see Requirements Discovery) — this epic is built and verified against local substitutes throughout.

---

## Changes

| Change | Description | Dependencies |
|--------|-------------|--------------|
| [litellm-gateway](./changes/litellm-gateway/SPEC.md) | LiteLLM proxy config, Haiku/Sonnet routing, prompt caching, Batch API stub, health check | None |
| [nexus-supervisor](./changes/nexus-supervisor/SPEC.md) | Python `DomainConfig`/`DomainRegistry` mirror + `domains/mcat` registration, intent classification, `AgentInput` assembly, tenant context | litellm-gateway |
| [langgraph-state-machine](./changes/langgraph-state-machine/SPEC.md) | Dynamic per-agent graph, handoff-conditioned edges, in-memory checkpointing, HITL escalation | nexus-supervisor |
| [database-wiring](./changes/database-wiring/SPEC.md) | Replace agent placeholder behaviors with real reads/writes against `core-data-schema`'s tables | nexus-supervisor |
| [sse-endpoint](./changes/sse-endpoint/SPEC.md) | `POST /api/chat`, JWT auth, SSE streaming, error handling | langgraph-state-machine, database-wiring |

## Acceptance Criteria

- [x] **AC1:** Given all 5 child changes are merged, when a student sends `POST /api/chat`, then they receive a streamed response from ARIA, MIRA, or QUINN without any code path referencing a hardcoded agent list. Verified: `test_chat_endpoint.py` end-to-end, plus `test_no_domain_leakage.py`'s automated grep audit of `nexus/`/`domains/_contracts/`.
- [x] **AC2:** Given ARIA's existing frustration handoff logic, when it fires during a live session, then LangGraph transitions to MIRA's node with full prior context (no cold start). Verified twice: directly in `test_turn_runner.py` (asserting MIRA's response contains ARIA's dynamically-produced `session_notes`) and end-to-end over HTTP in `test_chat_endpoint.py`.
- [x] **AC3:** Given a request for a tenant other than the caller's own, when any query executes, then it returns zero rows. Verified with genuine RLS enforcement (non-superuser `app_backend` role, not the default superuser) in `test_repositories.py`.
- [x] **AC4:** Given no real Anthropic/Supabase/JWT credentials exist in this environment, when this epic is verified, then every integration point is demonstrated against a local substitute. Confirmed: LLM calls behind mocked/protocol-based test doubles, all database work against a real local Postgres 17 + pgvector instance (not skipped or faked), JWT against a locally-generated test secret.

## Cross-Cutting Concerns

- **Local-substitute verification (see Requirements Discovery):** No real credentials for Anthropic, Supabase `service_role`, or Supabase Auth JWT signing exist in this environment. Every child change is verified against a local stand-in: intent classification and any LLM call sit behind protocols with non-LLM-backed test implementations; database-wiring reuses a local Postgres instance with `core-data-schema`'s 7 migrations reapplied (same method as that epic); JWT validation is tested against a test secret, not Supabase's real signing key.
- **Domain-agnosticism:** `nexus-supervisor` and `langgraph-state-machine` must not import or reference `domains/mcat` directly for their control-flow logic — they operate purely on `DomainConfig`/`AgentDef`/`AgentOutput.suggested_handoff`, resolved via the self-registration `DomainRegistry` pattern already established in TypeScript (`changes/2026/07/09/baseagent-domainconfig-contracts/`) and mirrored here in Python.
- **Tenant scoping reuse:** All database access in `database-wiring` reuses `current_tenant()`/`tenant_id` exactly as designed in `core-data-schema` — no new isolation mechanism invented.
- **Direct Postgres access, not PostgREST:** `database-wiring` connects via a raw Postgres client (`asyncpg`), not the `supabase-py` REST client — pgvector similarity queries (`<=>` operator) aren't cleanly expressible through PostgREST, and a backend service connecting directly to Postgres with an elevated role is the standard "service_role" pattern regardless of client library (see that child's Gaps & Assumptions).

## Domain Updates

### Glossary Terms

No new terms — `NEXUS`, `LangGraph`, `LiteLLM`, `Handoff`, `HITL Escalation Bus` are all pre-existing in `specs/domain/glossary.md`/`specs/architecture/overview.md`. This epic implements what those entries already describe.

## Out of Scope

- Redis-backed session checkpointing — `langgraph-state-machine` uses in-memory checkpointing for this phase, per your explicit "Redis or in-memory for Phase 1" framing.
- Real HITL notification/paging infrastructure — `risk_level == 'high'` escalation is a logged/flagged terminal state, not a real Slack/PagerDuty integration.
- Langfuse observability wiring, Ragas/EVAL batch job implementation — `litellm-gateway`'s Batch API config is a stub for that future work, not a working pipeline.
- SAGE, VERA, SCOUT, ATLAS — the remaining unimplemented MCAT agents. This epic's design must not hardcode "3 agents," but it's only exercised against the 3 that exist.
- Real end-to-end testing against live Anthropic/Supabase — explicit decision, see Requirements Discovery.
- Frontend (`apps/web`) integration with `/api/chat` — backend endpoint only.

## Requirements Discovery

### Questions & Answers

| Step | Question | Answer |
|------|----------|--------|
| Scope | How should real-credential touchpoints (LiteLLM→Anthropic, Supabase service_role, JWT validation) be handled? | Local substitutes throughout — reuse local Postgres from `core-data-schema`, stub/protocol-based LLM calls, test JWT secret. No real API costs or production writes in this session. |
| Scope | Where does the Python `DomainConfig` mirror + `domains/mcat` registration belong? | Folded into `nexus-supervisor`, same pattern as the `BaseAgent`/`AgentInput` Python mirrors built for ARIA. |

### User Feedback

- User provided the full 5-sub-change breakdown, dependency order, and explicitly flagged the Python `DomainConfig` gap themselves before I raised it.

## References

- `changes/2026/07/10/aria-agent/`, `changes/2026/07/15/mira-agent/`, `changes/2026/07/15/quinn-agent/` — the 3 agents this epic connects
- `changes/2026/07/16/core-data-schema/` — the database this epic wires agents to
- `changes/2026/07/09/baseagent-domainconfig-contracts/` — the TypeScript `DomainConfig`/`DomainRegistry` this epic mirrors in Python
- `CLAUDE.md` — Agent Contract Architecture, Tech Stack (LiteLLM, LangGraph)
- `specs/architecture/overview.md` — L1 (LiteLLM Gateway), L2 (NEXUS, LangGraph, HITL Escalation Bus)
