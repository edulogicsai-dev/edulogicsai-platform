# Episodic Memory

## Definition

`episodic_memory` (`apps/web/supabase/migrations/20260716000004_episodic_memory.sql`) stores session summaries with pgvector embeddings for ANN retrieval. This is the real implementation of what ARIA, MIRA, and QUINN's `session_notes`/`episodic_context` JSON-marker heuristic (`changes/2026/07/10/aria-agent/`, `changes/2026/07/15/mira-agent/`, `changes/2026/07/15/quinn-agent/`) has stood in for — none of those agents are wired to this table yet (schema only).

## Schema

```sql
create table episodic_memory (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null references tenants(id),
  student_id uuid not null,
  session_id uuid not null references agent_sessions(id) on delete cascade,
  summary text not null,
  embedding vector(1536),        -- placeholder dimension, not yet finalized
  relevance_score real check (relevance_score is null or (relevance_score >= 0 and relevance_score <= 1)),
  occurred_at timestamptz not null default now(),
  foreign key (student_id, tenant_id) references student_profiles(user_id, tenant_id) on delete cascade
);

create index episodic_memory_embedding_idx on episodic_memory
  using ivfflat (embedding vector_cosine_ops) with (lists = 100);
```

Field shape maps directly to the existing `EpisodicMemory` contract in `packages/core`/`apps/backend` (`id`, `summary`, `occurredAt` ↔ `occurred_at`, `relevanceScore` ↔ `relevance_score`).

## RLS

Students can `select`/`insert` only their own episodic memories, scoped to tenant. No `update`/`delete` — append-only.

## Open Questions

- Embedding dimension (`1536`) is a placeholder pending Mem0's actual embedding-model choice.
- `ivfflat` vs `hnsw` — chosen for guaranteed compatibility; revisit once the project's pgvector version is confirmed (verified locally as 0.8.5, which does support `hnsw`, but this hasn't been decided against the actual deployed Supabase project).

## Related

- [`Agent Session`](./agent-session.md) — FK target.
- [`Student Profile`](./student-profile.md) — composite FK target.
