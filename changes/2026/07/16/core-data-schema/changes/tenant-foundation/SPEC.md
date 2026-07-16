---
title: Tenant Foundation — tenants table, current_tenant(), pgvector
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

Establish the multi-tenant foundation every other table in this epic depends on: a `tenants` lookup table, a `current_tenant()` RLS helper function, and the `pgvector` extension (enabled once, here, for `episodic-memory` and `domain-content` to share).

### Background

`specs/domain/glossary.md` already documents `Tenant` as "a domain product instance (mcat, gre, dat)" mapping to `tenant_id` in every DB row, and `CLAUDE.md`'s architecture rules already state `tenant_id` must scope every DB query. Neither exists in the database yet — this change makes that documented invariant real and enforceable, and establishes the pattern every subsequent child change in this epic reuses verbatim.

### Current State

No `tenants` table, no `current_tenant()` function, no `pgvector` extension in this Supabase project (see epic SPEC.md Background — this project is currently the unmodified Vercel Stripe-billing starter).

---

## Functional Requirements

### FR1: `tenants` Table

**Behavior:**
- `tenants` shall have: `id text primary key` (the domain id, e.g. `'mcat'`), `name text not null` (display name, e.g. `'MCATai'`), `subdomain text not null unique` (e.g. `'app.mcatai.co'`), `created_at timestamptz not null default now()`.
- Seeded with one row: `('mcat', 'MCATai', 'app.mcatai.co')`. `gre`/`dat` rows are added when those domains are actually built (Phase 2 per `CLAUDE.md`), not speculatively seeded now.
- RLS: enabled, with a public-read policy (`using (true)`) — every table that references `tenants(id)` needs to be able to read it, and the set of valid tenants is not sensitive.

### FR2: `current_tenant()` RLS Helper

**Behavior:**
- A `stable` SQL function returning the caller's current tenant id as `text`.
- Reads from, in order: (1) the Supabase Auth JWT's `app_metadata.tenant_id` claim (via the `request.jwt.claims` PostgREST session variable — the standard Supabase RLS pattern for frontend/PostgREST-originated queries), falling back to (2) a `app.tenant_id` Postgres session variable (`current_setting('app.tenant_id', true)`), for direct-connection queries from `apps/backend` (FastAPI) that don't go through PostgREST/JWT.
- Returns `null` if neither is set — RLS policies using `tenant_id = current_tenant()` then correctly deny all rows (a `null = null` comparison is `null`, not `true`), rather than accidentally allowing cross-tenant access.

### FR3: pgvector Extension

**Behavior:**
- `create extension if not exists vector;` — enabled exactly once, here. `episodic-memory` and `domain-content` (later children) depend on this and must not re-declare it.

## Acceptance Criteria

- [ ] **AC1:** Given the migration is applied, when `select * from tenants` is run, then it returns exactly one row (`mcat`).
- [ ] **AC2:** Given a Postgres session with `app.tenant_id` set to `'mcat'` via `set local`, when `select current_tenant()` is run, then it returns `'mcat'`.
- [ ] **AC3:** Given a Postgres session with neither the JWT claim nor `app.tenant_id` set, when `select current_tenant()` is run, then it returns `null`.
- [ ] **AC4:** Given the migration is applied, when `select extname from pg_extension where extname = 'vector'` is run, then it returns one row.
- [ ] **AC5:** Given the existing Stripe billing tables, when this migration is applied, then none of them are altered.

## Technical Design

### Migration

`apps/web/supabase/migrations/<timestamp>_tenant_foundation.sql`:

```sql
create table tenants (
  id text primary key,
  name text not null,
  subdomain text not null unique,
  created_at timestamptz not null default now()
);

alter table tenants enable row level security;
create policy "Public read access to tenants." on tenants for select using (true);

insert into tenants (id, name, subdomain) values
  ('mcat', 'MCATai', 'app.mcatai.co');

create or replace function current_tenant() returns text
language sql stable
as $$
  select coalesce(
    nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'tenant_id',
    nullif(current_setting('app.tenant_id', true), '')
  );
$$;

create extension if not exists vector;
```

## Specs Directory Changes

### Changes Summary

| Path | Action | Description |
|------|--------|--------------|
| specs/domain/definitions/tenant.md | Create | The `tenants` table, `current_tenant()`, and the epic-wide RLS convention |

## Domain Updates

### Definition Specs

| File | Description | Action |
|------|-------------|--------|
| `tenant.md` | `tenants` table, `current_tenant()`, RLS convention reused by every subsequent child change | create |

## Testing Strategy

### Integration Tests (Supabase local/CI)

| Test Case | Expected Behavior |
|-----------|--------------------|
| Migration applies cleanly on a fresh local Supabase instance | No errors; `tenants` has 1 row |
| `current_tenant()` with `app.tenant_id` set | Returns the set value |
| `current_tenant()` with nothing set | Returns `null` |
| Existing Stripe tables (`users`, `customers`, `products`, `prices`, `subscriptions`) | Unchanged, still function |

## Out of Scope

- `gre`/`dat` tenant rows — added when those domains are actually built.
- Wiring `apps/backend` to actually `set local app.tenant_id` per request — this change only defines the function; call-site wiring is separate future work (NEXUS/request-handling doesn't exist yet).

## References

- `changes/2026/07/16/core-data-schema/SPEC.md` — parent epic
- `specs/domain/glossary.md` — pre-existing `Tenant` entry
