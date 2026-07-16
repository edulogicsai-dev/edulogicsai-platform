---
title: Domain Content Store - Implementation Plan
change: domain-content
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-16
sdd_version: 7.3.0
---

## Overview

Implementation plan for: Domain Content Store (pgvector RAG)

Specification: [SPEC.md](./SPEC.md)

## Affected Components

- apps/web/supabase (existing, untracked as an SDD component)

## Prerequisites

- `tenant-foundation` — complete. Provides `tenants`, `current_tenant()`, pgvector extension.

## Implementation Phases

### Phase 1: Migration

**Component:** apps/web/supabase
**Standards:** N/A

Tasks:
- [x] Create `apps/web/supabase/migrations/20260716000005_domain_content.sql` per SPEC.md's Technical Design
- [x] Apply locally and verify AC1–AC4 — AC2 specifically verified as a real RLS denial (granted `insert` privilege first, then confirmed the failure is "violates row-level security policy," not a missing-grant error)

Deliverables:
- Migration file created and verified against real Postgres

### Phase 2: Domain Documentation

**Standards:** domain-population (per sdd:domain-population skill)

Tasks:
- [x] Create `specs/domain/definitions/domain-content.md`

Deliverables:
- `specs/domain/definitions/domain-content.md` created

### Phase 3: Review

**Standards:** N/A (manual)

Tasks:
- [x] Spec compliance review against all 4 acceptance criteria — all verified via psql
- [x] Confirm `create extension vector` NOT re-declared here — confirmed via grep
- [x] Confirm `specs/` changes match SPEC.md's declared Specs Directory Changes exactly

## Expected Files

### Files to Create

| File | Component | Description |
|------|-----------|--------------|
| `apps/web/supabase/migrations/<timestamp>_domain_content.sql` | apps/web/supabase | `domain_content` table + ivfflat index + RLS |
| `specs/domain/definitions/domain-content.md` | docs | Domain definition |

## Implementation State

### Current Phase

- **Phase:** Complete (all 3 phases)
- **Status:** complete
- **Last Updated:** 2026-07-16

### Completed Phases

| Phase | Completed | Notes |
|-------|-----------|-------|
| 1 | [x] | |
| 2 | [x] | |
| 3 | [x] | |

### Actual Files Changed

| File | Action | Phase | Notes |
|------|--------|-------|-------|
| `apps/web/supabase/migrations/20260716000005_domain_content.sql` | Create | 1 | |
| `specs/domain/definitions/domain-content.md` | Create | 2 | |

### Blockers

- (none)

## Dependencies

- `tenant-foundation`

## Risks

| Risk | Mitigation |
|------|------------|
| Same embedding-dimension placeholder risk as `episodic-memory` | Documented in SPEC.md; no real data written yet |
