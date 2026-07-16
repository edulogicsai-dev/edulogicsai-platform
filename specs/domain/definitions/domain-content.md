# Domain Content

## Definition

`domain_content` (`apps/web/supabase/migrations/20260716000005_domain_content.sql`) is the RAG knowledge base per domain (`mcat_content`, later `gre_content`). Isolation between domains is achieved entirely via `tenant_id` + RLS — **one shared table**, not physically separate tables per domain — the same mechanism every other table in this epic uses.

## Schema

```sql
create table domain_content (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null references tenants(id),
  source_id text not null,       -- maps to ContentChunk.sourceId
  content text not null,         -- maps to ContentChunk.text
  embedding vector(1536),        -- placeholder dimension, not yet finalized
  created_at timestamptz not null default now()
);
```

## RLS — Read-Only for Students

Authenticated students can `select` content scoped to their tenant. **No `insert`/`update`/`delete` policies** — content ingestion (Firecrawl/LlamaIndex re-indexing, per `specs/architecture/overview.md`) is a `service_role` job that bypasses RLS entirely, not an end-user operation. Verified locally: granting the authenticated test role `insert` privilege and attempting a write still fails with `new row violates row-level security policy` — the denial is RLS itself, not a missing table grant.

## Related

- [`Tenant`](./tenant.md) — the isolation mechanism (`tenant_id` + RLS), not a separate namespace column.
- [`Episodic Memory`](./episodic-memory.md) — same ANN-index approach (`ivfflat`/cosine).
