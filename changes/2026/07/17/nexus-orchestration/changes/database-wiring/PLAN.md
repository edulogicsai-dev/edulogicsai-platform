---
title: Database Wiring - Implementation Plan
change: database-wiring
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-17
sdd_version: 7.3.0
---

## Overview

Implementation plan for: Database Wiring

Specification: [SPEC.md](./SPEC.md)

## Affected Components

- apps/backend (existing, untracked as an SDD component)

## Prerequisites

- `nexus-supervisor` — complete. Provides `assemble_agent_input`, `set_tenant_context`.
- `core-data-schema` — complete. All 7 tables this change wires against.

## Implementation Phases

### Phase 1: Connection Pool + Tenant Scope

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [x] Add `asyncpg` to `apps/backend/pyproject.toml` dependencies
- [x] Create `apps/backend/db/pool.py`: `create_pool(dsn)` (FR1)
- [x] Create `apps/backend/db/tenant_scope.py`: `tenant_scoped(pool, tenant_id, acting_user_id=None)` context manager — `acting_user_id` added during implementation (see SPEC.md Gaps & Assumptions: `auth.uid()` doesn't resolve for backend-originated connections without it)
- [x] Added `nexus.tenant_context.set_acting_user()` (new, alongside the existing `set_tenant_context`) to make this possible without inventing new RLS policies

Deliverables:
- `tenant_scoped()` implements FR1

### Phase 2: Repositories

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [x] Create `apps/backend/db/repositories.py`: `AgentSessionRepository`, `EpisodicMemoryRepository`, `StudentProfileRepository`, `DomainContentRepository`, `ConceptMasteryRepository` (FR2, FR6)
- [x] `DomainContentRepository.search()` uses Postgres full-text search (`to_tsvector`/`plainto_tsquery`), not raw `ILIKE` — a materially better non-vector fallback, still no embedding model required
- [x] `StudentProfileRepository.load_profile()` joins to the Stripe starter's `users.full_name` for `displayName`, since `student_profiles` has no such column — discovered mismatch, documented in SPEC.md
- [x] `AgentSessionRepository.increment_turn_count()` gained a `student_id` parameter beyond the original sketch — required for `acting_user_id`

Deliverables:
- All 5 repositories implement FR2

### Phase 3: Persistence Wrappers

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [x] Create `apps/backend/db/agent_persistence.py`: `PersistentAgent` (FR3), `QuinnPersistentAgent` (FR4)
- [x] Modify `apps/backend/domains/mcat/agents/quinn.py`: thread `ease_factor` through the pending marker, populate `mastery_update` on evaluation (FR4) — with an explicit note about the field-repurposing discrepancy
- [x] Additionally prefixed `MasteryDelta.conceptId` with `tenant_id` at the DB-write boundary only — discovered `concept_mastery`'s domain-prefix check constraint didn't match QUINN's (never-prefixed) internal concept tracking; student-facing text stays unprefixed

Deliverables:
- `PersistentAgent`/`QuinnPersistentAgent` implement FR3/FR4
- QUINN's existing 10 tests still pass unchanged — verified twice (once right after the `ease_factor`/`mastery_update` edit, once after the `conceptId` prefix fix)

### Phase 4: Live AgentInput Assembly

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [x] Create `apps/backend/db/live_agent_input.py`: `build_live_agent_input(...)` composing real `student_profile`/`episodic_context`/`retrieved_chunks` via the repositories, plus in-process `session_history` (FR5)

Deliverables:
- Function implements FR5, with the `session_history` gap documented inline

### Phase 5: Integration Tests

**Standards:** N/A (pytest, against local Postgres)

Tasks:
- [x] Set up local Postgres 17 + pgvector (same as `core-data-schema`), reapplied its 7 migrations **plus the original Stripe starter migration** (needed for `users.full_name`, not anticipated in the original plan — see SPEC.md Gaps & Assumptions)
- [x] Created a dedicated non-superuser `app_backend` role for repository-under-test connections — the default local role (`bennguyen`) is a superuser and bypasses RLS unconditionally, which would have made every RLS assertion meaningless (same lesson as `core-data-schema`)
- [x] Fixed the local stub `auth.users` table (missing `raw_user_meta_data`, needed by the starter's `handle_new_user()` trigger)
- [x] `test_repositories.py`: AC1–AC4, AC7 (genuine RLS-enforced tenant isolation, not just "we never inserted there")
- [x] `test_agent_persistence.py`: `PersistentAgent` real write + output-identity check (AC5)
- [x] `test_agent_persistence.py`: `QuinnPersistentAgent` ease_factor adjustment, both correct and incorrect answers (AC6)
- [x] `test_live_agent_input.py`: direct test of FR5's composition function (not explicitly required by an AC, but the actual integration point `sse-endpoint` depends on)
- [x] Re-run full existing suite (all prior changes' tests) — confirm AC8

Deliverables:
- Full pytest suite passing (63/63 — 54 existing + 9 new), covering AC1–AC8, against real Postgres with genuine RLS enforcement

### Phase 6: Review

**Standards:** N/A (manual)

Tasks:
- [x] Spec compliance review against all 8 acceptance criteria — all satisfied
- [x] Confirm QUINN's modification didn't regress any of its 10 existing tests — confirmed twice
- [x] Confirm every repository method routes through `tenant_scoped()` — verified by inspection (all 7 repository methods do)

## Expected Files

### Files to Create

| File | Component | Description |
|------|-----------|--------------|
| `apps/backend/db/pool.py` | apps/backend | Connection pool |
| `apps/backend/db/tenant_scope.py` | apps/backend | `tenant_scoped()` |
| `apps/backend/db/repositories.py` | apps/backend | 5 repositories |
| `apps/backend/db/agent_persistence.py` | apps/backend | `PersistentAgent`, `QuinnPersistentAgent` |
| `apps/backend/db/live_agent_input.py` | apps/backend | `build_live_agent_input`, session_history cache |
| `apps/backend/tests/test_repositories.py` | apps/backend | |
| `apps/backend/tests/test_agent_persistence.py` | apps/backend | |
| `apps/backend/tests/test_live_agent_input.py` | apps/backend | |

### Files to Modify

| File | Description |
|------|-------------|
| `apps/backend/domains/mcat/agents/quinn.py` | Thread `ease_factor`, populate `mastery_update` with domain-prefixed `conceptId` (FR4) |
| `apps/backend/nexus/tenant_context.py` | Added `set_acting_user()` |
| `apps/backend/pyproject.toml` | Add `asyncpg` dependency |

## Implementation State

### Current Phase

- **Phase:** Complete (all 6 phases)
- **Status:** complete
- **Last Updated:** 2026-07-17

### Completed Phases

| Phase | Completed | Notes |
|-------|-----------|-------|
| 1 | [x] | `acting_user_id` added mid-phase after discovering `auth.uid()` doesn't resolve for backend connections |
| 2 | [x] | `StudentProfile`/`student_profiles` mismatch and `increment_turn_count` signature gap both discovered here |
| 3 | [x] | `concept_id` domain-prefix constraint mismatch discovered and fixed; QUINN's 10 tests re-verified |
| 4 | [x] | |
| 5 | [x] | Superuser-bypasses-RLS risk caught before any test ran meaninglessly; starter migration + `raw_user_meta_data` gaps found and fixed |
| 6 | [x] | |

### Actual Files Changed

| File | Action | Phase | Notes |
|------|--------|-------|-------|
| `apps/backend/db/pool.py` | Create | 1 | |
| `apps/backend/db/tenant_scope.py` | Create | 1 | |
| `apps/backend/nexus/tenant_context.py` | Modify | 1 | Added `set_acting_user()` |
| `apps/backend/db/repositories.py` | Create | 2 | |
| `apps/backend/db/agent_persistence.py` | Create | 3 | |
| `apps/backend/domains/mcat/agents/quinn.py` | Modify | 3 | `ease_factor` threading, `mastery_update` population, `conceptId` domain-prefix fix |
| `apps/backend/db/live_agent_input.py` | Create | 4 | |
| `apps/backend/tests/test_repositories.py` | Create | 5 | |
| `apps/backend/tests/test_agent_persistence.py` | Create | 5 | |
| `apps/backend/tests/test_live_agent_input.py` | Create | 5 | |
| `apps/backend/pyproject.toml` | Modify | 1 | Added `asyncpg` |

### Blockers

- (none)

## Dependencies

- `nexus-supervisor`, `core-data-schema`.

## Risks

| Risk | Mitigation |
|------|------------|
| Modifying `quinn.py` (shipped, tested code) risks regressing its 10 existing tests | Explicit re-run gate before proceeding past Phase 3; AC8 covers it |
| No `messages` table means `session_history` doesn't survive a restart | Documented as an Open Question in SPEC.md, not silently ignored |
| Text-search RAG fallback isn't representative of real retrieval quality | Interface designed so real vector search is a drop-in replacement later |
