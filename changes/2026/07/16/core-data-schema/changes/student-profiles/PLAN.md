---
title: Student Profiles - Implementation Plan
change: student-profiles
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-16
sdd_version: 7.3.0
---

## Overview

Implementation plan for: Student Profiles

Specification: [SPEC.md](./SPEC.md)

## Affected Components

- apps/web/supabase (existing, untracked as an SDD component — same gap as tenant-foundation)

## Prerequisites

- `tenant-foundation` — complete. Provides `tenants` table and `current_tenant()`.

## Implementation Phases

### Phase 1: Migration

**Component:** apps/web/supabase
**Standards:** N/A

Tasks:
- [x] Create `apps/web/supabase/migrations/20260716000002_student_profiles.sql` per SPEC.md's Technical Design
- [x] Apply locally (local Postgres 17 + pgvector instance, same as tenant-foundation) and verify AC1–AC4, including real RLS enforcement via a non-superuser `app_authenticated` role (the table owner bypasses RLS by default, so testing as the owner would have been meaningless)

Deliverables:
- Migration file created and verified, including actual RLS cross-tenant isolation (not just reviewed)

### Phase 2: Domain Documentation

**Standards:** domain-population (per sdd:domain-population skill)

Tasks:
- [x] Create `specs/domain/definitions/student-profile.md`

Deliverables:
- `specs/domain/definitions/student-profile.md` created

### Phase 3: Review

**Standards:** N/A (manual)

Tasks:
- [x] Spec compliance review against all 4 acceptance criteria — all verified via psql
- [x] Confirm `specs/` changes match SPEC.md's declared Specs Directory Changes exactly

## Expected Files

### Files to Create

| File | Component | Description |
|------|-----------|--------------|
| `apps/web/supabase/migrations/<timestamp>_student_profiles.sql` | apps/web/supabase | `student_profiles` table + RLS |
| `specs/domain/definitions/student-profile.md` | docs | Domain definition |

## Implementation State

### Current Phase

- **Phase:** Complete (all 3 phases)
- **Status:** complete
- **Last Updated:** 2026-07-16

### Completed Phases

| Phase | Completed | Notes |
|-------|-----------|-------|
| 1 | [x] | RLS cross-tenant isolation verified via non-superuser role, not just reviewed |
| 2 | [x] | |
| 3 | [x] | |

### Actual Files Changed

| File | Action | Phase | Notes |
|------|--------|-------|-------|
| `apps/web/supabase/migrations/20260716000002_student_profiles.sql` | Create | 1 | |
| `specs/domain/definitions/student-profile.md` | Create | 2 | |

### Blockers

- (none)

## Dependencies

- `tenant-foundation`

## Risks

| Risk | Mitigation |
|------|------------|
| No real auth/signup flow exists yet to test against real `auth.users` rows | Test with manually inserted `auth.users` rows in local Supabase for now |
