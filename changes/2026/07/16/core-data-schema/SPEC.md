---
title: Core Data Platform — Multi-Tenant Database Schema
type: epic
status: active
domain: platform
issue: TBD
created: 2026-07-16
updated: 2026-07-16
sdd_version: 7.3.0
affected_components: []
---

## Overview

Build the core multi-tenant Supabase (Postgres + pgvector + Auth) schema for the tutoring platform: student profiles, agent sessions, episodic memory, domain content (RAG), concept mastery (FSRS), and a versioned prompt registry. This epic was paused early (before `packages/core`'s `BaseAgent`/`DomainConfig` contracts existed) and resumes now that those contracts, and three working MCAT agents (ARIA, MIRA, QUINN), exist as concrete consumers this schema must serve.

### Background

`apps/web` already contains an unmodified Vercel "Next.js Subscription Payments" starter (`apps/web/schema.sql`, `apps/web/supabase/migrations/20230530034630_init.sql`): `users`, `customers`, `products`, `prices`, `subscriptions` — Stripe billing tables, single-tenant (per-user), no `tenant_id`, no pgvector. Per explicit decision (see Requirements Discovery), **this epic does not touch those tables** — multi-tenant billing is deferred to a separate future change when GREai needs it.

Meanwhile, ARIA, MIRA, and QUINN (`changes/2026/07/10/aria-agent/`, `changes/2026/07/15/mira-agent/`, `changes/2026/07/15/quinn-agent/`) have been shipping without any real persistence layer — they encode cross-turn state (frustration streaks, handoff context, pending questions) into `AgentOutput.session_notes`, read back via a fixture-only `AgentInput.episodic_context`, because there is no database to actually persist and query. This epic's `episodic_memory` and `concept_mastery` tables are what those heuristics were always meant to be superseded by.

### Current State

- No multi-tenant tables exist anywhere in this Supabase project.
- No `tenants` concept exists in the database (only in docs — `specs/domain/glossary.md`, `CLAUDE.md`).
- No pgvector extension enabled.
- `packages/core`/`apps/backend`'s `AgentInput`/`AgentOutput` contracts (`tenant_id`, `student_id`, `session_id`, `episodic_context: EpisodicMemory[]`, etc.) already exist and are stable — this schema is designed to be queried into those shapes, not the reverse.

---

## Changes

| Change | Description | Dependencies |
|--------|-------------|--------------|
| [tenant-foundation](./changes/tenant-foundation/SPEC.md) | `tenants` lookup table, `current_tenant()` RLS helper, pgvector extension enabled | None |
| [student-profiles](./changes/student-profiles/SPEC.md) | `student_profiles` — FK to `auth.users`, own `tenant_id` | tenant-foundation |
| [agent-sessions](./changes/agent-sessions/SPEC.md) | `agent_sessions` — one row per conversation | tenant-foundation, student-profiles |
| [episodic-memory](./changes/episodic-memory/SPEC.md) | `episodic_memory` — session summaries + pgvector embeddings | tenant-foundation, agent-sessions |
| [domain-content](./changes/domain-content/SPEC.md) | `domain_content` — per-domain pgvector RAG namespace | tenant-foundation |
| [concept-mastery](./changes/concept-mastery/SPEC.md) | `concept_mastery` — per student per concept, FSRS fields | tenant-foundation, student-profiles |
| [prompt-registry](./changes/prompt-registry/SPEC.md) | `prompt_registry` — versioned agent system prompts | tenant-foundation |

## Acceptance Criteria

- [x] **AC1:** Given all 7 child changes are merged, when any new table introduced by this epic is inspected, then it has a `tenant_id text not null references tenants(id)` column. Verified: all of `student_profiles`, `agent_sessions`, `episodic_memory`, `domain_content`, `concept_mastery`, `prompt_registry` have it (`tenants` itself is the lookup table, not tenant-scoped).
- [x] **AC2:** Given any table introduced by this epic, when its RLS policies are inspected, then every policy enforces `tenant_id = current_tenant()`. Verified via `psql` with a real non-superuser role for every table with policies; `prompt_registry` has no policies at all (private/service_role-only), vacuously satisfying this and matching its own spec's design.
- [x] **AC3:** Given the existing Stripe billing tables, when this epic completes, then none of them have been modified. Verified via `git status --porcelain` (no diff) and a full fresh-database apply of the real starter migration plus all 7 new ones together (12 tables, no conflicts).
- [x] **AC4:** Given `pgvector` is enabled once (in tenant-foundation), when `episodic-memory` and `domain-content` are implemented, then neither re-declares the extension. Verified via `grep` and successful sequential apply with no "already exists" errors for those two files specifically.
- [x] **AC5:** Given a `concept_id` value anywhere in this schema, when inspected, then it follows the `<domain>::<slug>` convention. Verified: `concept_mastery.concept_id` has a `check (concept_id like '%::%')` constraint, tested against both a valid (`mcat::enzyme_kinetics`) and invalid value.

## Cross-Cutting Concerns

- **`tenant_id` type and value:** `text`, matching `specs/domain/glossary.md`'s existing documented convention (`'mcat'`, `'gre'`, `'dat'` — lowercase domain ids), not `uuid`. Every new table's `tenant_id` is a foreign key to `tenants(id)`, giving referential integrity instead of an unchecked string.
- **RLS pattern:** Every table introduced by this epic enables RLS and defines policies using `tenant_id = current_tenant()`, where `current_tenant()` (defined in tenant-foundation) is a `SECURITY DEFINER` SQL function reading the caller's tenant from their Supabase Auth JWT `app_metadata` claim.
- **pgvector:** Enabled exactly once (tenant-foundation's migration), since `episodic-memory` and `domain-content` both depend on it — avoids a duplicate `create extension` across two migrations.
- **Migration location/naming:** `apps/web/supabase/migrations/<timestamp>_<description>.sql`, Supabase CLI convention (matches the existing `20230530034630_init.sql`) — corrected in `CLAUDE.md` as part of this epic's scoping (it previously stated a nonexistent root-level `supabase/migrations/00N_description.sql` path).
- **No retrofit of existing tables:** `users`, `customers`, `products`, `prices`, `subscriptions` (the Vercel SaaS starter) are explicitly untouched by this epic — see Out of Scope.
- **Supersedes agent heuristics:** `episodic-memory` and `concept-mastery` are designed to eventually replace the `session_notes`/`episodic_context` JSON-marker pattern ARIA/MIRA/QUINN currently use as a stand-in (see each agent's SPEC.md Open Questions) — but wiring the agents to actually read/write these tables is explicitly out of scope for this epic (schema only, not agent integration — see Out of Scope).

## Domain Updates

### Glossary Terms

No new terms — `Tenant`, `Handoff`, `Memory Tiers`, `ContentIndex`, `EvalRubric`, `PromptRegistry` are all pre-existing in `specs/domain/glossary.md`. This epic implements what those entries already describe.

### Definition Specs

| File | Description | Action |
|------|-------------|--------|
| `tenant.md` | The `tenants` table, `current_tenant()` RLS pattern, and the epic-wide `tenant_id` convention | create (in tenant-foundation child) |

Each other child change creates its own definition spec for its table (see each child's SPEC.md).

## Out of Scope

- Retrofitting `tenant_id` onto the existing Stripe billing tables (`users`, `customers`, `products`, `prices`, `subscriptions`) — explicit decision, deferred to a future multi-tenant billing change when GREai needs it.
- Wiring ARIA/MIRA/QUINN to actually read from/write to `episodic_memory`/`concept_mastery` instead of their current `session_notes`/`episodic_context` heuristics — schema only in this epic; agent integration is separate future work.
- NEXUS, LangGraph orchestration, LiteLLM routing — none of this exists yet.
- A real Langfuse-backed PromptRegistry client — `prompt-registry` is the database table only; the Python/TypeScript client code that reads/writes it is out of scope here (see `prompt-registry` child SPEC.md).
- A normalized `concepts` catalog table — `concept_id` is free-text (`domain::slug` convention), not a foreign key to a separate concepts table, consistent with `specs/domain/glossary.md`'s existing convention.

## Requirements Discovery

### Questions & Answers

| Step | Question | Answer |
|------|----------|--------|
| Scope | Should tenant_id retrofit onto the existing Stripe billing tables? | No — new tutoring tables only. Billing tables are managed by the Vercel starter's webhook handlers; breaking that delays launch for zero tutoring value. Multi-tenant billing is a separate future change. |
| Scope | Should student profiles be new columns on `users`, or a separate table? | Separate `student_profiles` table — learning state and billing identity are different bounded contexts. References `auth.users` directly (not the starter's `users` table), owns its own `tenant_id`. |

### User Feedback

- User provided the full 7-table breakdown, tenant_id/RLS invariants, and concept_id convention up front.
- User asked me to inspect `apps/web/schema.sql`/`apps/web/supabase/` before drafting, specifically to avoid conflicting with the existing Vercel SaaS starter — this shaped both Requirements Discovery answers above.
