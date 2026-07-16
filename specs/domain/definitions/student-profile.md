# Student Profile

## Definition

`student_profiles` (`apps/web/supabase/migrations/20260716000002_student_profiles.sql`) holds per-tenant learning state for a student — separate from the existing Vercel starter's `users` table (billing identity: `billing_address`, `payment_method`) and separate from `auth.users` (Supabase-managed identity).

## Schema

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
```

Primary key is `(user_id, tenant_id)`, not `user_id` alone — a student can have independent profiles across tenants (e.g. MCATai and, later, GREai).

## RLS

Students can `select`/`insert`/`update` only their own profile (`auth.uid() = user_id`), scoped to their tenant (`tenant_id = current_tenant()`). No `delete` policy — profile deletion is an admin/service-role operation.

## Related

- [`Tenant`](./tenant.md) — `tenant_id` FK target, `current_tenant()`.
- Consumed (eventually) by `agent_sessions` and `concept_mastery` via composite FK `(student_id, tenant_id)` / `(user_id, tenant_id)`.
