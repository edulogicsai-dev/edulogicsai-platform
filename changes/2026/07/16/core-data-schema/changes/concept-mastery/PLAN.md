---
title: Concept Mastery - Implementation Plan
change: concept-mastery
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-16
sdd_version: 7.3.0
---

## Overview

Implementation plan for: Concept Mastery (Spaced Repetition)

Specification: [SPEC.md](./SPEC.md)

## Affected Components

- apps/web/supabase (existing, untracked as an SDD component)

## Prerequisites

- `tenant-foundation` — complete.
- `student-profiles` — complete. Provides composite FK target.

## Implementation Phases

### Phase 1: Migration

**Component:** apps/web/supabase
**Standards:** N/A

Tasks:
- [x] Create `apps/web/supabase/migrations/20260716000006_concept_mastery.sql` per SPEC.md's Technical Design
- [x] Apply locally and verify AC1–AC5 (including RLS isolation)

Deliverables:
- Migration file created and verified against real Postgres

### Phase 2: Domain Documentation

**Standards:** domain-population (per sdd:domain-population skill)

Tasks:
- [x] Create `specs/domain/definitions/concept-mastery.md`, explicitly noting the `ease_factor` vs. FSRS-5 `stability`/`difficulty` naming discrepancy (see SPEC.md Gaps & Assumptions)

Deliverables:
- `specs/domain/definitions/concept-mastery.md` created

### Phase 3: Review

**Standards:** N/A (manual)

Tasks:
- [x] Spec compliance review against all 5 acceptance criteria — all verified via psql
- [x] Confirm `specs/` changes match SPEC.md's declared Specs Directory Changes exactly

## Expected Files

### Files to Create

| File | Component | Description |
|------|-----------|--------------|
| `apps/web/supabase/migrations/<timestamp>_concept_mastery.sql` | apps/web/supabase | `concept_mastery` table + RLS |
| `specs/domain/definitions/concept-mastery.md` | docs | Domain definition |

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
| `apps/web/supabase/migrations/20260716000006_concept_mastery.sql` | Create | 1 | |
| `specs/domain/definitions/concept-mastery.md` | Create | 2 | |

### Blockers

- (none)

## Dependencies

- `tenant-foundation`, `student-profiles`

## Risks

| Risk | Mitigation |
|------|------------|
| `ease_factor` may not match what `ts-fsrs` (FSRS-5) actually needs (`stability`/`difficulty`) | Flagged explicitly in SPEC.md as an Open Question; no scheduling logic depends on this yet, so revising the schema later is low-cost |
