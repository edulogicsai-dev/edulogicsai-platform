# Tenant

## Definition

A `Tenant` is a domain product instance (`mcat`, `gre`, `dat`), per `specs/domain/glossary.md`'s pre-existing entry. The `tenants` table (`apps/web/supabase/migrations/20260716000001_tenant_foundation.sql`) makes this concept real and enforceable in the database, and `current_tenant()` is the RLS helper every subsequent table in the `core-data-schema` epic uses to enforce tenant isolation.

## Schema

```sql
create table tenants (
  id text primary key,           -- 'mcat', 'gre', 'dat'
  name text not null,            -- 'MCATai'
  subdomain text not null unique,-- 'app.mcatai.co'
  created_at timestamptz not null default now()
);
```

Seeded with one row (`mcat`) — `gre`/`dat` are added when those domains are actually built (Phase 2 per `CLAUDE.md`).

## `current_tenant()`

```sql
create or replace function current_tenant() returns text
language sql stable
as $$
  select coalesce(
    nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'tenant_id',
    nullif(current_setting('app.tenant_id', true), '')
  );
$$;
```

Reads the tenant id from, in order: (1) the Supabase Auth JWT's `app_metadata.tenant_id` claim (via the `request.jwt.claims` PostgREST session variable — populated automatically for frontend/PostgREST-originated queries), falling back to (2) a `app.tenant_id` Postgres session variable, set via `set local` for direct-connection queries from `apps/backend` that don't go through PostgREST/JWT. Returns `null` if neither is set, which correctly denies all rows under any `tenant_id = current_tenant()` RLS policy (a `null` comparison is never `true`).

## RLS Convention (used by every table in this epic)

```sql
tenant_id text not null references tenants(id),
...
alter table <table> enable row level security;
create policy "..." on <table> for select using (tenant_id = current_tenant());
```

## Related

- Every table in `changes/2026/07/16/core-data-schema/` reuses this pattern.
- `pgvector` extension is also enabled by this same migration (shared prerequisite for `episodic_memory` and `domain_content`).
