---
title: Student Profiles
type: feature
status: active
domain: platform
issue: TBD
created: 2026-07-16
updated: 2026-07-16
sdd_version: 7.3.0
parent_epic: ../../SPEC.md
affected_components: []
---

## Overview

A `student_profiles` table holding per-tenant learning state (test date, score goal, current score, study streak), linked to Supabase Auth (`auth.users`), separate from the existing Stripe-billing `users` table.

### Background

Per explicit decision (see epic SPEC.md Requirements Discovery): student learning state is a different bounded context from billing identity, so this is a new table, not new columns on the existing starter's `users` table. A student can plausibly have profiles in more than one tenant (e.g. MCATai and, later, GREai) independently, so the natural key is `(user_id, tenant_id)`, not `user_id` alone.

### Current State

No `student_profiles` table exists. `auth.users` (Supabase Auth, managed) and the starter's `users` table (billing identity) both exist; neither holds learning state.

---

## Functional Requirements

### FR1: `student_profiles` Table

**Behavior:**
- Columns: `user_id uuid not null references auth.users(id) on delete cascade`, `tenant_id text not null references tenants(id)`, `test_date date` (planned MCAT test date), `score_goal int` (target score), `current_score int` (most recent practice/diagnostic score), `study_streak int not null default 0` (consecutive days studied), `created_at timestamptz not null default now()`, `updated_at timestamptz not null default now()`.
- Primary key: `(user_id, tenant_id)` — one profile per student per tenant.
- References `auth.users` directly (Supabase-managed), not the starter's `users` table — learning identity is keyed off the same underlying auth identity as billing, but the tables themselves stay decoupled.

**Constraints:**
- `test_date`, `score_goal`, `current_score` are nullable — a freshly-created profile (e.g. right after signup) has none of these yet.
- `study_streak` defaults to `0`, never null.

### FR2: RLS

**Behavior:**
- A student can `select`/`insert`/`update` only their own profile (`auth.uid() = user_id`), scoped to their tenant (`tenant_id = current_tenant()`) — both conditions required together.
- No `delete` policy — profile deletion (if ever needed) is an admin/service-role operation, not exposed to end users.

## Acceptance Criteria

- [ ] **AC1:** Given the migration is applied, when a row is inserted with `tenant_id = 'mcat'` referencing a real `auth.users.id`, then it succeeds.
- [ ] **AC2:** Given a row insert with a non-existent `tenant_id`, when attempted, then it fails on the foreign key constraint.
- [ ] **AC3:** Given two students in different tenants, when one queries `student_profiles` as an authenticated user, then RLS returns only their own row, not the other tenant's.
- [ ] **AC4:** Given a `student_profiles` row, when `study_streak` is not explicitly provided on insert, then it defaults to `0`.

## Technical Design

### Migration

`apps/web/supabase/migrations/<timestamp>_student_profiles.sql`:

```sql
create table student_profiles (
  user_id uuid not null references auth.users(id) on delete cascade,
  tenant_id text not null references tenants(id),
  test_date date,
  score_goal int,
  current_score int,
  study_streak int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, tenant_id)
);

alter table student_profiles enable row level security;

create policy "Students can view own profile." on student_profiles
  for select using (auth.uid() = user_id and tenant_id = current_tenant());

create policy "Students can insert own profile." on student_profiles
  for insert with check (auth.uid() = user_id and tenant_id = current_tenant());

create policy "Students can update own profile." on student_profiles
  for update using (auth.uid() = user_id and tenant_id = current_tenant());
```

## Specs Directory Changes

### Changes Summary

| Path | Action | Description |
|------|--------|--------------|
| specs/domain/definitions/student-profile.md | Create | The `student_profiles` table and its relationship to `auth.users` |

## Domain Updates

### Definition Specs

| File | Description | Action |
|------|-------------|--------|
| `student-profile.md` | `student_profiles` table definition | create |

## Testing Strategy

### Integration Tests (Supabase local/CI)

| Test Case | Expected Behavior |
|-----------|--------------------|
| Insert with valid `tenant_id` | Succeeds |
| Insert with invalid `tenant_id` | FK violation |
| RLS: student A queries as authenticated user | Only sees own row |
| Insert without `study_streak` | Defaults to `0` |

## Dependencies

### Internal Dependencies

| Component | Reason |
|-----------|--------|
| `tenant-foundation` | `tenants` table, `current_tenant()` function |

## Out of Scope

- Wiring `packages/core`'s `StudentProfile` TypeScript type or the Python Pydantic mirror to actually query this table — those types (`userId`, `displayName`, `createdAt`) are part of the `AgentInput` contract and currently constructed from fixtures/placeholders in ARIA/MIRA/QUINN; connecting them to this table is separate future work.

## References

- `changes/2026/07/16/core-data-schema/SPEC.md` — parent epic
- `changes/2026/07/16/core-data-schema/changes/tenant-foundation/SPEC.md` — `tenants`, `current_tenant()`
