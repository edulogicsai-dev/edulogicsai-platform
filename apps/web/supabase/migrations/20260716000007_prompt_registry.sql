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
