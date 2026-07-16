---
title: Prompt Registry
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

A `prompt_registry` table holding versioned agent system prompts per tenant, with an active-version flag and an A/B experiment reference — the database-backed counterpart to the `FilePromptRegistryClient` placeholder ARIA/MIRA/QUINN currently use.

### Background

`changes/2026/07/10/aria-agent/SPEC.md` FR6 already defines a `PromptRegistryClient` protocol with a file-based implementation reading `domains/{domain}/prompts/{agent_id}_{version}.md`, explicitly flagging the real Langfuse-backed registry as future work. This table is a step toward that — a durable, queryable store — though wiring the client to actually read from it is separate future work (see Out of Scope).

### Current State

No `prompt_registry` table. ARIA/MIRA/QUINN's prompts live only as markdown files (`domains/mcat/prompts/{aria,mira,quinn}_v1.md`), each with YAML frontmatter (`prompt_id`, `tenant_id`, `version`, `status`) — see Gaps & Assumptions for how that frontmatter relates to this table's columns.

---

## Functional Requirements

### FR1: `prompt_registry` Table

**Behavior:**
- Columns: `id uuid primary key default gen_random_uuid()`, `tenant_id text not null references tenants(id)`, `agent_id text not null` (e.g. `'aria'`), `version text not null` (e.g. `'v1'`), `content text not null` (the full prompt text), `active boolean not null default false`, `ab_experiment_id text` (nullable — most prompts aren't part of an experiment), `created_at timestamptz not null default now()`.
- Unique constraint on `(tenant_id, agent_id, version)` — no duplicate versions per agent per tenant.
- At most one `active = true` row per `(tenant_id, agent_id)` — enforced via a partial unique index, not application logic alone.

### FR2: RLS — Private Table

**Behavior:**
- RLS enabled, **no policies** for the authenticated role — prompts are internal system configuration, not student-facing data. Only `service_role` (server-side, per `CLAUDE.md`'s rule that `service_role` never reaches the client) can read/write, same pattern as the existing starter's `customers` table (`apps/web/schema.sql`: "No policies as this is a private table that the user must not have access to").

## Acceptance Criteria

- [ ] **AC1:** Given a row for `(tenant_id='mcat', agent_id='aria', version='v1')`, when a second row with the same triple is inserted, then it fails the unique constraint.
- [ ] **AC2:** Given an active row for `('mcat', 'aria')`, when a second `active = true` row for the same `(tenant_id, agent_id)` is inserted, then it fails the partial unique index.
- [ ] **AC3:** Given the authenticated (non-service-role) Postgres role, when any query against `prompt_registry` is attempted, then RLS denies it (no policies exist).
- [ ] **AC4:** Given `ab_experiment_id` is omitted, when a row is inserted, then it's `null`.

## Technical Design

### Migration

`apps/web/supabase/migrations/<timestamp>_prompt_registry.sql`:

```sql
create table prompt_registry (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null references tenants(id),
  agent_id text not null,
  version text not null,
  content text not null,
  active boolean not null default false,
  ab_experiment_id text,
  created_at timestamptz not null default now(),
  unique (tenant_id, agent_id, version)
);

create unique index prompt_registry_one_active_idx on prompt_registry (tenant_id, agent_id)
  where active;

alter table prompt_registry enable row level security;
-- No policies: private table, service_role only (same pattern as the existing
-- `customers` table in apps/web/schema.sql).
```

## Specs Directory Changes

### Changes Summary

| Path | Action | Description |
|------|--------|--------------|
| specs/domain/definitions/prompt-registry.md | Create | The `prompt_registry` table and its relationship to the existing markdown prompt files |

## Domain Updates

### Definition Specs

| File | Description | Action |
|------|-------------|--------|
| `prompt-registry.md` | `prompt_registry` table definition, noting the frontmatter-vs-column naming discrepancy | create |

## Testing Strategy

### Integration Tests (Supabase local/CI)

| Test Case | Expected Behavior |
|-----------|--------------------|
| Insert duplicate `(tenant_id, agent_id, version)` | Unique constraint violation |
| Insert second `active = true` row for same `(tenant_id, agent_id)` | Partial unique index violation |
| Query as authenticated (non-service) role | RLS denies (no rows, no policy) |
| Insert without `ab_experiment_id` | Defaults to `null` |

## Dependencies

### Internal Dependencies

| Component | Reason |
|-----------|--------|
| `tenant-foundation` | `tenants` table |

## Out of Scope

- Wiring `FilePromptRegistryClient`/`PromptRegistryClient` (`apps/backend/prompt_registry/client.py`) to actually read from this table instead of the filesystem — schema only.
- Migrating the existing `domains/mcat/prompts/*.md` files' content into this table — a data-population task, not a schema task.
- Real Langfuse integration (versioning UI, A/B test orchestration) — `ab_experiment_id` is just a reference column here.

## Gaps & Assumptions

- The existing prompt markdown files' YAML frontmatter uses `prompt_id`/`status` (e.g. `prompt_id: aria`, `status: active`), while this table uses `agent_id`/`active` (boolean). These aren't the same shape — `prompt_id` ↔ `agent_id` is a naming difference, and `status: active` (string) ↔ `active` (boolean) is a type difference. Reconciling them is part of whatever future change actually wires the `PromptRegistryClient` to this table, not this schema-only change.

## Open Questions

- [ ] Should the markdown frontmatter (`prompt_id`, `status`) be renamed to match this table's columns (`agent_id`, `active`) now, or should this table's columns be renamed to match the frontmatter instead, whenever the two are actually connected?

## References

- `changes/2026/07/16/core-data-schema/SPEC.md` — parent epic
- `changes/2026/07/10/aria-agent/SPEC.md` FR6 — `PromptRegistryClient` protocol this table backs
- `domains/mcat/prompts/aria_v1.md`, `mira_v1.md`, `quinn_v1.md` — existing frontmatter this table's shape should eventually reconcile with
