# Prompt Registry

## Definition

`prompt_registry` (`apps/web/supabase/migrations/20260716000007_prompt_registry.sql`) holds versioned agent system prompts per tenant, with an active-version flag and an A/B experiment reference. This is the database-backed counterpart to the `FilePromptRegistryClient` placeholder ARIA/MIRA/QUINN currently use (`changes/2026/07/10/aria-agent/SPEC.md` FR6) — not yet wired up to it.

## Schema

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
```

At most one `active = true` row per `(tenant_id, agent_id)`, enforced by the partial unique index — verified locally: inserting a second active version for the same agent/tenant fails.

## RLS — Private Table

RLS enabled, **no policies** — prompts are internal system configuration, `service_role`-only, same pattern as the existing `customers` table (`apps/web/schema.sql`). Verified locally: a granted `select` privilege still returns zero rows for a non-service role, since RLS with no policies denies everything.

## Known Discrepancy — Frontmatter Naming

The existing prompt markdown files (`domains/mcat/prompts/{aria,mira,quinn}_v1.md`) use YAML frontmatter `prompt_id`/`status` (string `"active"`), while this table uses `agent_id`/`active` (boolean). These aren't the same shape. Reconciling them is future work for whichever change actually wires the `PromptRegistryClient` to this table.

## Related

- [`Tenant`](./tenant.md) — FK target.
- `changes/2026/07/10/aria-agent/SPEC.md` FR6 — the `PromptRegistryClient` protocol this table backs.
