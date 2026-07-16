# Agent Session

## Definition

`agent_sessions` (`apps/web/supabase/migrations/20260716000003_agent_sessions.sql`) tracks every conversation between a student and a domain agent — one row per session.

## Schema

```sql
create table agent_sessions (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null references tenants(id),
  student_id uuid not null,
  agent_id text not null,       -- 'aria', 'mira', 'quinn' -- free text, no FK (agent roster lives in code via DomainConfig)
  started_at timestamptz not null default now(),
  ended_at timestamptz,         -- null while in progress
  turn_count int not null default 0,
  session_notes text,
  foreign key (student_id, tenant_id) references student_profiles(user_id, tenant_id) on delete cascade
);
```

## RLS

Students can `select`/`insert`/`update` only their own sessions, scoped to tenant. No `delete` policy.

## Related

- [`Student Profile`](./student-profile.md) — composite FK target `(student_id, tenant_id)`.
- [`Episodic Memory`](./episodic-memory.md) — references `agent_sessions(id)`.
