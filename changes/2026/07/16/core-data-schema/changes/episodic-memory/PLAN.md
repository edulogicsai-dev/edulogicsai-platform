---
title: Episodic Memory - Implementation Plan
change: episodic-memory
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-16
sdd_version: 7.3.0
---

## Overview

Implementation plan for: Episodic Memory (pgvector)

Specification: [SPEC.md](./SPEC.md)

## Affected Components

- apps/web/supabase (existing, untracked as an SDD component)

## Prerequisites

- `tenant-foundation` — complete. Provides pgvector extension.
- `agent-sessions` — complete. Provides FK target.

## Implementation Phases

### Phase 1: Migration

**Component:** apps/web/supabase
**Standards:** N/A

Tasks:
- [x] Create `apps/web/supabase/migrations/20260716000004_episodic_memory.sql` per SPEC.md's Technical Design
- [x] Apply locally and verify AC1–AC5, including an `explain` check confirming the planner actually uses `episodic_memory_embedding_idx` (not just that the index exists)

Deliverables:
- Migration file created and verified against real Postgres 17 + pgvector 0.8.5

### Phase 2: Domain Documentation

**Standards:** domain-population (per sdd:domain-population skill)

Tasks:
- [x] Create `specs/domain/definitions/episodic-memory.md`

Deliverables:
- `specs/domain/definitions/episodic-memory.md` created

### Phase 3: Review

**Standards:** N/A (manual)

Tasks:
- [x] Spec compliance review against all 5 acceptance criteria — all verified via psql
- [x] Confirm `create extension vector` is NOT re-declared here (already enabled by tenant-foundation) — confirmed via grep
- [x] Confirm `specs/` changes match SPEC.md's declared Specs Directory Changes exactly

## Expected Files

### Files to Create

| File | Component | Description |
|------|-----------|--------------|
| `apps/web/supabase/migrations/<timestamp>_episodic_memory.sql` | apps/web/supabase | `episodic_memory` table + ivfflat index + RLS |
| `specs/domain/definitions/episodic-memory.md` | docs | Domain definition |

## Implementation State

### Current Phase

- **Phase:** Complete (all 3 phases)
- **Status:** complete
- **Last Updated:** 2026-07-16

### Completed Phases

| Phase | Completed | Notes |
|-------|-----------|-------|
| 1 | [x] | pgvector 0.8.5 confirmed to support hnsw too, but ivfflat kept per SPEC.md's original reasoning (production Supabase pgvector version still unconfirmed) |
| 2 | [x] | |
| 3 | [x] | |

### Actual Files Changed

| File | Action | Phase | Notes |
|------|--------|-------|-------|
| `apps/web/supabase/migrations/20260716000004_episodic_memory.sql` | Create | 1 | |
| `specs/domain/definitions/episodic-memory.md` | Create | 2 | |

### Blockers

- (none)

## Dependencies

- `tenant-foundation`, `agent-sessions`

## Risks

| Risk | Mitigation |
|------|------------|
| Embedding dimension (1536) is a placeholder, not yet confirmed against Mem0's actual model choice | Documented explicitly in SPEC.md Gaps & Assumptions; changing it later is a straightforward migration since no real embeddings exist yet |
| `ivfflat` vs `hnsw` index choice not yet validated against this project's actual pgvector version | Tracked as an Open Question in SPEC.md |
