---
title: Domain Content Store (pgvector RAG)
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

A `domain_content` table holding the RAG knowledge base per domain (`mcat_content`, and later `gre_content`), with pgvector embeddings for retrieval.

### Background

`DomainConfig.contentIndex` (`packages/core`) already names this concept (e.g. `'mcat_content'`) per domain. Rather than physically separate tables per domain (`mcat_content` table, `gre_content` table, ...), this change uses **one shared `domain_content` table isolated by `tenant_id`** — the same mechanism every other table in this epic uses, rather than a special-cased alternative. `tenant_id` (`'mcat'`, `'gre'`, ...) *is* the namespace; there's no separate namespace column.

### Current State

No content store exists. `AgentInput.retrieved_chunks` (the contract ARIA/MIRA/QUINN consume) is currently always populated from test fixtures, never real retrieval.

---

## Functional Requirements

### FR1: `domain_content` Table

**Behavior:**
- Columns: `id uuid primary key default gen_random_uuid()`, `tenant_id text not null references tenants(id)`, `source_id text not null` (maps to `ContentChunk.sourceId` in the existing contract), `content text not null` (maps to `ContentChunk.text`), `embedding vector(1536)` (same placeholder-dimension caveat as `episodic-memory`), `created_at timestamptz not null default now()`.
- Isolation between domains (`mcat_content` vs. `gre_content`) is achieved entirely via `tenant_id` + RLS — not separate tables.

### FR2: ANN Index

**Behavior:**
- Same `ivfflat`/cosine-distance approach as `episodic-memory`, for consistency (see that change's FR2 rationale).

### FR3: RLS — Read-Only for Students

**Behavior:**
- Authenticated students can `select` content scoped to their tenant (`tenant_id = current_tenant()`) — content is a shared knowledge base within a domain, not per-student.
- No `insert`/`update`/`delete` policies for the authenticated role — content ingestion (per `specs/architecture/overview.md`'s "Content Refresh: Firecrawl monitors domain sources, LlamaIndex re-index") is a service-role/admin job that bypasses RLS entirely (standard Supabase `service_role` behavior), not an end-user operation.

## Acceptance Criteria

- [ ] **AC1:** Given content rows for both `tenant_id = 'mcat'` and (hypothetically) `'gre'`, when a student authenticated under `'mcat'` queries `domain_content`, then only `mcat` rows are returned.
- [ ] **AC2:** Given the authenticated (non-service-role) Postgres role, when an `insert`/`update`/`delete` is attempted against `domain_content`, then RLS denies it.
- [ ] **AC3:** Given rows with embeddings, when an ANN similarity query is run, then the ivfflat index is used.
- [ ] **AC4:** Given the pgvector extension enabled by `tenant-foundation`, when this migration runs, then it does not re-declare `create extension vector`.

## Technical Design

### Migration

`apps/web/supabase/migrations/<timestamp>_domain_content.sql`:

```sql
create table domain_content (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null references tenants(id),
  source_id text not null,
  content text not null,
  embedding vector(1536),
  created_at timestamptz not null default now()
);

create index domain_content_embedding_idx on domain_content
  using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create index domain_content_tenant_idx on domain_content (tenant_id);

alter table domain_content enable row level security;

create policy "Authenticated users can read own-tenant content." on domain_content
  for select using (tenant_id = current_tenant());
```

## Specs Directory Changes

### Changes Summary

| Path | Action | Description |
|------|--------|--------------|
| specs/domain/definitions/domain-content.md | Create | The `domain_content` table and its tenant-based isolation approach |

## Domain Updates

### Definition Specs

| File | Description | Action |
|------|-------------|--------|
| `domain-content.md` | `domain_content` table definition | create |

## Testing Strategy

### Integration Tests (Supabase local/CI)

| Test Case | Expected Behavior |
|-----------|--------------------|
| Query as authenticated user under tenant A | Only tenant A rows returned |
| Insert as authenticated (non-service) role | RLS denies |
| Insert as service_role | Succeeds (bypasses RLS) |
| ANN query with `explain` | Uses ivfflat index |

## Dependencies

### Internal Dependencies

| Component | Reason |
|-----------|--------|
| `tenant-foundation` | `tenants`, `current_tenant()`, pgvector extension |

## Out of Scope

- The actual content ingestion pipeline (Firecrawl monitoring, LlamaIndex re-indexing) — table only.
- Wiring ARIA/MIRA/QUINN to query this table for `retrieved_chunks` instead of test fixtures.
- Finalizing the embedding dimension (same open question as `episodic-memory`).

## References

- `changes/2026/07/16/core-data-schema/SPEC.md` — parent epic
- `changes/2026/07/16/core-data-schema/changes/episodic-memory/SPEC.md` — shared ANN-index rationale
- `specs/architecture/overview.md` — Content Refresh (Firecrawl, LlamaIndex)
