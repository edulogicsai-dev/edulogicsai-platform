---
title: Agent Sessions
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

An `agent_sessions` table tracking every conversation between a student and a domain agent — one row per session, referencing the student's tenant-scoped profile.

### Current State

No `agent_sessions` table exists. ARIA/MIRA/QUINN currently have no record of sessions at all beyond what's passed in `AgentInput.session_id` per request (no persistence).

---

## Functional Requirements

### FR1: `agent_sessions` Table

**Behavior:**
- Columns: `id uuid primary key default gen_random_uuid()`, `tenant_id text not null references tenants(id)`, `student_id uuid not null`, `agent_id text not null` (e.g. `'aria'`, `'mira'`, `'quinn'` — free text, no FK; the agent roster lives in code via `DomainConfig`/`AgentDef`, not the database), `started_at timestamptz not null default now()`, `ended_at timestamptz` (null while in progress), `turn_count int not null default 0`, `session_notes text`.
- Composite foreign key `(student_id, tenant_id) references student_profiles(user_id, tenant_id) on delete cascade` — a session cannot exist without a corresponding tenant-scoped student profile.

**Constraints:**
- `ended_at` is nullable — a session may still be in progress.
- `turn_count` defaults to `0`; incrementing it is application logic, not DB-enforced here.

### FR2: RLS

**Behavior:**
- A student can `select`/`insert`/`update` only their own sessions (`auth.uid() = student_id`), scoped to their tenant.
- No `delete` policy — session deletion is not an end-user operation.

## Acceptance Criteria

- [ ] **AC1:** Given a `student_profiles` row exists for `(user_id, tenant_id)`, when an `agent_sessions` row is inserted for that same pair, then it succeeds.
- [ ] **AC2:** Given no matching `student_profiles` row, when an `agent_sessions` insert is attempted, then it fails on the foreign key constraint.
- [ ] **AC3:** Given a session with `ended_at` null, when queried, then it's treated as in-progress (no constraint forces `ended_at` to be set).
- [ ] **AC4:** Given a session insert without `turn_count`, when inserted, then it defaults to `0`.
- [ ] **AC5:** Given two students, when one queries `agent_sessions` as an authenticated user, then RLS returns only their own sessions.

## Technical Design

### Migration

`apps/web/supabase/migrations/<timestamp>_agent_sessions.sql`:

```sql
create table agent_sessions (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null references tenants(id),
  student_id uuid not null,
  agent_id text not null,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  turn_count int not null default 0,
  session_notes text,
  foreign key (student_id, tenant_id) references student_profiles(user_id, tenant_id) on delete cascade
);

create index agent_sessions_student_tenant_idx on agent_sessions (student_id, tenant_id);

alter table agent_sessions enable row level security;

create policy "Students can view own sessions." on agent_sessions
  for select using (auth.uid() = student_id and tenant_id = current_tenant());

create policy "Students can insert own sessions." on agent_sessions
  for insert with check (auth.uid() = student_id and tenant_id = current_tenant());

create policy "Students can update own sessions." on agent_sessions
  for update using (auth.uid() = student_id and tenant_id = current_tenant());
```

## Specs Directory Changes

### Changes Summary

| Path | Action | Description |
|------|--------|--------------|
| specs/domain/definitions/agent-session.md | Create | The `agent_sessions` table |

## Domain Updates

### Definition Specs

| File | Description | Action |
|------|-------------|--------|
| `agent-session.md` | `agent_sessions` table definition | create |

## Testing Strategy

### Integration Tests (Supabase local/CI)

| Test Case | Expected Behavior |
|-----------|--------------------|
| Insert with valid `(student_id, tenant_id)` matching a `student_profiles` row | Succeeds |
| Insert with no matching `student_profiles` row | FK violation |
| Insert without `ended_at`/`turn_count` | `ended_at` null, `turn_count` 0 |
| RLS: student queries sessions | Only own rows returned |

## Dependencies

### Internal Dependencies

| Component | Reason |
|-----------|--------|
| `tenant-foundation` | `tenants`, `current_tenant()` |
| `student-profiles` | Composite FK target |

## Out of Scope

- Wiring ARIA/MIRA/QUINN to actually create/update rows here — schema only.
- A trigger auto-incrementing `turn_count` — application-side responsibility for now.

## References

- `changes/2026/07/16/core-data-schema/SPEC.md` — parent epic
- `changes/2026/07/16/core-data-schema/changes/student-profiles/SPEC.md`
