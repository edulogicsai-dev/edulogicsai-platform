---
title: Episodic Memory (pgvector)
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

An `episodic_memory` table storing session summaries with pgvector embeddings, enabling approximate-nearest-neighbor (ANN) retrieval of relevant past context. This is what ARIA/MIRA/QUINN's `session_notes`/`episodic_context` JSON-marker heuristic (`changes/2026/07/10/aria-agent/`, `changes/2026/07/15/mira-agent/`, `changes/2026/07/15/quinn-agent/`) was always meant to be superseded by.

### Current State

No `episodic_memory` table, no embeddings anywhere. The three shipped MCAT agents fake cross-turn memory via `AgentOutput.session_notes` strings, re-read from `AgentInput.episodic_context` fixtures in tests — there's no real storage or similarity search.

---

## Functional Requirements

### FR1: `episodic_memory` Table

**Behavior:**
- Columns: `id uuid primary key default gen_random_uuid()`, `tenant_id text not null references tenants(id)`, `student_id uuid not null`, `session_id uuid not null references agent_sessions(id) on delete cascade`, `summary text not null`, `embedding vector(1536)`, `relevance_score real check (relevance_score is null or (relevance_score >= 0 and relevance_score <= 1))`, `occurred_at timestamptz not null default now()`.
- Composite foreign key `(student_id, tenant_id) references student_profiles(user_id, tenant_id) on delete cascade`.
- Field names/shape map directly to `packages/core`/`apps/backend`'s existing `EpisodicMemory` contract (`id`, `summary`, `occurredAt` ↔ `occurred_at`, `relevanceScore` ↔ `relevance_score`) — this table is designed to be the source that contract's values eventually come from.

**Constraints:**
- `embedding` dimension is `1536` as a **placeholder** matching common embedding models (e.g. OpenAI `text-embedding-3-small`/`ada-002`) — no embedding model has been finalized for Mem0 yet (see Gaps & Assumptions); this dimension may need to change before real embeddings are written.
- `relevance_score` is nullable and, when present, constrained to `[0, 1]`.

### FR2: ANN Index

**Behavior:**
- An `ivfflat` index on `embedding` using cosine distance (`vector_cosine_ops`), for approximate-nearest-neighbor retrieval.

**Constraints:**
- `ivfflat` chosen over `hnsw` for guaranteed compatibility regardless of this Supabase project's exact pgvector version (not yet verified) — revisit if `hnsw` is confirmed available and a better recall/performance tradeoff is wanted (see Open Questions).

### FR3: RLS

**Behavior:**
- A student can `select`/`insert` only their own episodic memories, scoped to tenant. No `update`/`delete` — episodic memory is append-only from the application's perspective.

## Acceptance Criteria

- [ ] **AC1:** Given a valid `agent_sessions` row and matching `student_profiles` row, when an `episodic_memory` row is inserted, then it succeeds.
- [ ] **AC2:** Given no matching `agent_sessions` row, when an insert is attempted, then it fails on the foreign key constraint.
- [ ] **AC3:** Given a `relevance_score` of `1.5`, when an insert is attempted, then it fails the check constraint.
- [ ] **AC4:** Given rows with embeddings, when an ANN similarity query (`order by embedding <=> query_vector limit N`) is run, then the ivfflat index is used (visible via `explain`).
- [ ] **AC5:** Given the pgvector extension enabled by `tenant-foundation`, when this migration runs, then it does not re-declare `create extension vector`.

## Technical Design

### Migration

`apps/web/supabase/migrations/<timestamp>_episodic_memory.sql`:

```sql
create table episodic_memory (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null references tenants(id),
  student_id uuid not null,
  session_id uuid not null references agent_sessions(id) on delete cascade,
  summary text not null,
  embedding vector(1536),
  relevance_score real check (relevance_score is null or (relevance_score >= 0 and relevance_score <= 1)),
  occurred_at timestamptz not null default now(),
  foreign key (student_id, tenant_id) references student_profiles(user_id, tenant_id) on delete cascade
);

create index episodic_memory_embedding_idx on episodic_memory
  using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create index episodic_memory_student_tenant_idx on episodic_memory (student_id, tenant_id);

alter table episodic_memory enable row level security;

create policy "Students can view own episodic memory." on episodic_memory
  for select using (auth.uid() = student_id and tenant_id = current_tenant());

create policy "Students can insert own episodic memory." on episodic_memory
  for insert with check (auth.uid() = student_id and tenant_id = current_tenant());
```

## Specs Directory Changes

### Changes Summary

| Path | Action | Description |
|------|--------|--------------|
| specs/domain/definitions/episodic-memory.md | Create | The `episodic_memory` table and its relationship to the agents' current heuristic |

## Domain Updates

### Definition Specs

| File | Description | Action |
|------|-------------|--------|
| `episodic-memory.md` | `episodic_memory` table definition, explicitly noting it's the intended replacement for ARIA/MIRA/QUINN's `session_notes` heuristic | create |

## Testing Strategy

### Integration Tests (Supabase local/CI)

| Test Case | Expected Behavior |
|-----------|--------------------|
| Insert with valid session/student FK | Succeeds |
| Insert with invalid session FK | FK violation |
| Insert with `relevance_score = 1.5` | Check constraint violation |
| ANN query with `explain` | Uses `episodic_memory_embedding_idx` |

## Dependencies

### Internal Dependencies

| Component | Reason |
|-----------|--------|
| `tenant-foundation` | `tenants`, `current_tenant()`, pgvector extension |
| `agent-sessions` | FK target |

## Out of Scope

- Actually wiring ARIA/MIRA/QUINN to write/query this table instead of their `session_notes` heuristic — schema only (tracked as an open item on all three agents' SPEC.md Open Questions).
- Finalizing the embedding model/dimension — `1536` is a placeholder (see Gaps & Assumptions).
- Mem0 integration itself (`packages/memory`) — out of scope.

## Gaps & Assumptions

- Embedding dimension (`1536`) assumes an OpenAI-family embedding model; not yet confirmed against what `packages/memory`/Mem0 will actually use. Changing it later requires a new migration (`alter column embedding type vector(N)`) and re-embedding existing rows.
- pgvector version on this Supabase project not yet verified — `ivfflat` chosen for safety; `hnsw` may be a better choice once confirmed available.

## Open Questions

- [ ] Should the `ivfflat` index be replaced with `hnsw` once the project's pgvector version is confirmed to support it?
- [ ] What embedding model/dimension will Mem0 actually use — is `1536` correct, or does it need to change before any real data is written?

## References

- `changes/2026/07/16/core-data-schema/SPEC.md` — parent epic
- `changes/2026/07/16/core-data-schema/changes/agent-sessions/SPEC.md`
- `changes/2026/07/10/aria-agent/SPEC.md`, `changes/2026/07/15/mira-agent/SPEC.md`, `changes/2026/07/15/quinn-agent/SPEC.md` — the heuristics this table supersedes
