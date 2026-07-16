---
title: Prompt Registry - Implementation Plan
change: prompt-registry
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-16
sdd_version: 7.3.0
---

## Overview

Implementation plan for: Prompt Registry

Specification: [SPEC.md](./SPEC.md)

## Affected Components

- apps/web/supabase (existing, untracked as an SDD component)

## Prerequisites

- `tenant-foundation` — complete. Provides `tenants` table.

## Implementation Phases

### Phase 1: Migration

**Component:** apps/web/supabase
**Standards:** N/A

Tasks:
- [x] Create `apps/web/supabase/migrations/20260716000007_prompt_registry.sql` per SPEC.md's Technical Design
- [x] Apply locally and verify AC1–AC4 — AC3 specifically verified with `select` privilege actually granted, confirming the zero-rows result is RLS-with-no-policies, not a missing GRANT

Deliverables:
- Migration file created and verified against real Postgres

### Phase 2: Domain Documentation

**Standards:** domain-population (per sdd:domain-population skill)

Tasks:
- [x] Create `specs/domain/definitions/prompt-registry.md`, noting the frontmatter-vs-column naming discrepancy (see SPEC.md Gaps & Assumptions)

Deliverables:
- `specs/domain/definitions/prompt-registry.md` created

### Phase 3: Review

**Standards:** N/A (manual)

Tasks:
- [x] Spec compliance review against all 4 acceptance criteria — all verified via psql
- [x] Confirm `specs/` changes match SPEC.md's declared Specs Directory Changes exactly

## Expected Files

### Files to Create

| File | Component | Description |
|------|-----------|--------------|
| `apps/web/supabase/migrations/<timestamp>_prompt_registry.sql` | apps/web/supabase | `prompt_registry` table + RLS (no policies, private) |
| `specs/domain/definitions/prompt-registry.md` | docs | Domain definition |

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
| `apps/web/supabase/migrations/20260716000007_prompt_registry.sql` | Create | 1 | |
| `specs/domain/definitions/prompt-registry.md` | Create | 2 | |

### Blockers

- (none)

## Dependencies

- `tenant-foundation`

## Risks

| Risk | Mitigation |
|------|------------|
| Naming/type mismatch between existing prompt `.md` frontmatter and this table's columns | Flagged explicitly in SPEC.md Gaps & Assumptions and Open Questions; no reconciliation attempted here |
