---
title: Core Data Platform — Multi-Tenant Database Schema - Implementation Plan
change: core-data-schema
type: epic
spec: ./SPEC.md
status: draft
created: 2026-07-16
sdd_version: 7.3.0
---

## Overview

Implementation plan for epic: Core Data Platform — Multi-Tenant Database Schema

Specification: [SPEC.md](./SPEC.md)

## Change Order

| # | Change | Description | Dependencies | Status |
|---|--------|-------------|--------------|--------|
| 1 | [tenant-foundation](./changes/tenant-foundation/PLAN.md) | `tenants` table, `current_tenant()`, pgvector extension | None | complete |
| 2 | [student-profiles](./changes/student-profiles/PLAN.md) | `student_profiles` | tenant-foundation | complete |
| 3 | [agent-sessions](./changes/agent-sessions/PLAN.md) | `agent_sessions` | tenant-foundation, student-profiles | complete |
| 4 | [episodic-memory](./changes/episodic-memory/PLAN.md) | `episodic_memory` (pgvector) | tenant-foundation, agent-sessions | complete |
| 5 | [domain-content](./changes/domain-content/PLAN.md) | `domain_content` (pgvector) | tenant-foundation | complete |
| 6 | [concept-mastery](./changes/concept-mastery/PLAN.md) | `concept_mastery` (FSRS) | tenant-foundation, student-profiles | complete |
| 7 | [prompt-registry](./changes/prompt-registry/PLAN.md) | `prompt_registry` | tenant-foundation | complete |

## Dependency Graph

```
tenant-foundation
    ├──► student-profiles
    │        ├──► agent-sessions ──► episodic-memory
    │        └──► concept-mastery
    ├──► domain-content
    └──► prompt-registry
```

`domain-content` and `prompt-registry` only depend on `tenant-foundation` and could, in principle, be implemented in parallel with the student-profiles/agent-sessions/episodic-memory chain — but this plan implements them in the numbered order above for a simpler, linear PR sequence.

## PR Strategy

One PR per child change. Branch naming: `epic/core-data-schema/<change-name>`.

Each child change is a single Supabase migration file under `apps/web/supabase/migrations/`, plus its own domain-definition spec file — small, independently reviewable, and independently revertible without affecting sibling tables (aside from the declared FK dependencies above).

## Progress Tracking

- [x] Change 1: tenant-foundation
- [x] Change 2: student-profiles
- [x] Change 3: agent-sessions
- [x] Change 4: episodic-memory
- [x] Change 5: domain-content
- [x] Change 6: concept-mastery
- [x] Change 7: prompt-registry

## Verification Summary

No Supabase CLI or Docker was available in this environment, so all 7 migrations were verified against a real local Postgres 17 + pgvector 0.8.5 instance (installed via Homebrew), not just reviewed by eye:

- Every migration applied cleanly, individually and as a full sequence from a fresh database.
- **Full real migration history verified end-to-end**: the existing Stripe starter migration (`20230530034630_init.sql`) plus all 7 new migrations were applied together on a clean database — all 12 tables (5 existing + 7 new) coexist with no conflicts.
- RLS was tested using a genuine non-superuser role (`app_authenticated`) plus stub `auth.uid()`/`auth.users` mimicking Supabase's real implementation — the table owner bypasses RLS by default, so testing as the owner would have proven nothing.
- Every acceptance criterion across all 7 child specs (34 ACs total) was verified via `psql`, including negative cases (FK violations, check constraint violations, RLS cross-tenant denial, RLS denial with privileges actually granted).
- `git diff` and a full fresh-migration-history apply both confirm zero modification to the existing Stripe billing tables (epic AC3).
- The scratch test database and local Postgres server were torn down after verification — nothing persists in this environment as a side effect.

## Resource Usage

| Change | Tokens (Input) | Tokens (Output) | Turns | Duration | Notes |
|--------|----------------|------------------|-------|----------|-------|
| tenant-foundation | - | - | - | | |
| student-profiles | - | - | - | | |
| agent-sessions | - | - | - | | |
| episodic-memory | - | - | - | | |
| domain-content | - | - | - | | |
| concept-mastery | - | - | - | | |
| prompt-registry | - | - | - | | |
| **Total** | **-** | **-** | **-** | **-** | |
