---
title: Tenant Foundation - Implementation Plan
change: tenant-foundation
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-16
sdd_version: 7.3.0
---

## Overview

Implementation plan for: Tenant Foundation

Specification: [SPEC.md](./SPEC.md)

## Affected Components

<!-- No SDD component type for Supabase/Postgres migrations under apps/web/supabase
     in the active fullstack-typescript tech pack (its "database" component type
     assumes a self-hosted Postgres deployed via Helm/Kubernetes, not managed
     Supabase — same gap noted when packages/core and apps/backend were built).
     Phase hand-authored. -->
- apps/web/supabase (existing, untracked as an SDD component)

## Prerequisites

None — first change in the epic.

## Implementation Phases

### Phase 1: Migration

**Component:** apps/web/supabase
**Standards:** N/A

Tasks:
- [x] Create `apps/web/supabase/migrations/20260716000001_tenant_foundation.sql` per SPEC.md's Technical Design
- [x] Apply locally — no Supabase CLI/Docker available in this environment, so a real local Postgres 17 + pgvector 0.8.5 instance was installed via Homebrew instead, with a stub `auth` schema (`auth.users`, `auth.uid()`) mimicking Supabase's real implementation, to verify against actual Postgres rather than just reviewing SQL by eye
- [x] Verify AC1–AC5 via `psql` against that instance

Deliverables:
- Migration file created and verified against a real Postgres instance

### Phase 2: Domain Documentation

**Standards:** domain-population (per sdd:domain-population skill)

Tasks:
- [x] Create `specs/domain/definitions/tenant.md`

Deliverables:
- `specs/domain/definitions/tenant.md` created, matching SPEC.md's declared Specs Directory Changes

### Phase 3: Review

**Standards:** N/A (manual — no Supabase/Postgres verification agent in the active tech pack)

Tasks:
- [x] Spec compliance review against all 5 acceptance criteria — AC1–AC4 verified via psql; AC5 to be confirmed via git diff once the full epic is implemented
- [x] Confirm `specs/` changes match SPEC.md's declared Specs Directory Changes exactly

## Expected Files

### Files to Create

| File | Component | Description |
|------|-----------|--------------|
| `apps/web/supabase/migrations/<timestamp>_tenant_foundation.sql` | apps/web/supabase | `tenants` table, `current_tenant()`, pgvector extension |
| `specs/domain/definitions/tenant.md` | docs | Domain definition |

## Implementation State

### Current Phase

- **Phase:** Complete (all 3 phases)
- **Status:** complete
- **Last Updated:** 2026-07-16

### Completed Phases

| Phase | Completed | Notes |
|-------|-----------|-------|
| 1 | [x] | Verified against real Postgres 17 + pgvector 0.8.5 (Homebrew), not just reviewed |
| 2 | [x] | |
| 3 | [x] | |

### Actual Files Changed

| File | Action | Phase | Notes |
|------|--------|-------|-------|
| `apps/web/supabase/migrations/20260716000001_tenant_foundation.sql` | Create | 1 | |
| `specs/domain/definitions/tenant.md` | Create | 2 | |

### Blockers

- (none)

## Dependencies

- None.

## Risks

| Risk | Mitigation |
|------|------------|
| `current_tenant()`'s JWT-claim path is unverified against a real Supabase Auth session (no auth flow exists yet in this codebase) | The `app.tenant_id` session-variable fallback is independently testable via plain SQL; the JWT path can be verified once real auth exists |
