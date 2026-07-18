---
title: Database Wiring
type: feature
status: active
domain: mcat
issue: TBD
created: 2026-07-17
updated: 2026-07-17
sdd_version: 7.3.0
parent_epic: ../../SPEC.md
affected_components: []
---

## Overview

Replace ARIA/MIRA/QUINN's placeholder behaviors (`write_episodic_memory()` no-ops, fixture-only `AgentInput` construction, QUINN's in-memory-only mastery tracking) with real reads/writes against `core-data-schema`'s tables, verified against a local Postgres instance (same method as that epic).

### Background

Every DB-shaped behavior across all 3 agents has been a deterministic placeholder until now: `write_episodic_memory` returns `None`; `session_notes`/`episodic_context` markers simulate memory that doesn't persist; QUINN's `ease_factor`-style tracking lives only inside one turn's marker string. `core-data-schema` built the real tables (`agent_sessions`, `episodic_memory`, `student_profiles`, `domain_content`, `concept_mastery`) months ago, but nothing has queried them yet.

### Current State

`BaseAgent.write_episodic_memory()` is a no-op in ARIA, MIRA, and QUINN. `assemble_agent_input()` (`nexus-supervisor`) takes already-fetched components as arguments but nothing fetches them for real. No database client, no connection pool, no repositories exist in `apps/backend`.

---

## Functional Requirements

### FR1: Connection Pool + Tenant-Scoped Query Helper

**Behavior:**
- `apps/backend/db/pool.py` shall create an `asyncpg` connection pool from a DSN (read from an environment variable, never hardcoded).
- `apps/backend/db/tenant_scope.py`'s `tenant_scoped(pool, tenant_id)` shall be an async context manager that acquires a connection, opens a transaction, and calls `nexus.tenant_context.set_tenant_context(conn, tenant_id)` (reusing the helper `nexus-supervisor` already defined) before yielding the connection — every query in this change goes through it, so RLS is enforced the same way for every repository method.

### FR2: Repositories

**Behavior:**
- `AgentSessionRepository`: `create_session(tenant_id, student_id, agent_id) -> session_id`; `increment_turn_count(session_id, tenant_id, student_id)` (`student_id` added during implementation — see Gaps & Assumptions).
- `EpisodicMemoryRepository`: `write(tenant_id, student_id, session_id, summary, relevance_score=None)`; `recent_for_student(tenant_id, student_id, limit=10) -> list[EpisodicMemory]`.
- `StudentProfileRepository`: `load_profile(tenant_id, user_id) -> StudentProfile`.
- `DomainContentRepository`: `search(tenant_id, query_text, limit=5) -> list[ContentChunk]`.
- `ConceptMasteryRepository`: `record_attempt(tenant_id, student_id, concept_id, correct: bool) -> (previous_ease_factor, new_ease_factor)` — upserts, adjusting `ease_factor` via a simplified SM-2-style rule (correct: `+0.1`, capped at `3.0`; incorrect: `-0.2`, floored at `1.3`), incrementing `review_count`, setting `last_reviewed_at`/`next_review`.

**Constraints:**
- Every repository method routes through `tenant_scoped()` (FR1) — no method accepts a raw connection or bypasses tenant scoping.

### FR3: `PersistentAgent` Wrapper — Real Episodic Memory Writes

**Behavior:**
- `apps/backend/db/agent_persistence.py`'s `PersistentAgent` shall wrap any `BaseAgent` instance, delegating `id`, `fetch_prompt()`, and `respond()` unchanged to the wrapped agent, and overriding only `write_episodic_memory()` to call `EpisodicMemoryRepository.write(...)` with the real values from `input`/`output`.
- Applied to ARIA and MIRA as-is (no code changes to `aria.py`/`mira.py`).

**Constraints:**
- Because `PersistentAgent` doesn't override `respond()`, and `BaseAgent.stream()` (unchanged, from `changes/2026/07/10/aria-agent/`) calls `respond()` then `write_episodic_memory()`, wrapping an agent this way requires zero changes to `BaseAgent` or the orchestration flow already built — only a new class.

### FR4: QUINN Mastery Wiring (Discrepancy, Flagged)

**Behavior:**
- `quinn.py`'s `quinn_pending` marker shall additionally carry `ease_factor` (defaulting to `2.5` on a fresh question, per `concept_mastery`'s default), threaded through `_present_fresh_question`/`_evaluate_answer`.
- On evaluating an answer, `quinn.py` shall populate `AgentOutput.mastery_update` with a `MasteryDelta` — **repurposing** its `previousStability`/`newStability` fields to carry the ease-factor values (not true FSRS stability), since `concept_mastery` uses `ease_factor`, not `stability`/`difficulty` (same known discrepancy already flagged in `changes/2026/07/16/core-data-schema/changes/concept-mastery/SPEC.md`).
- `QuinnPersistentAgent` (extends `PersistentAgent`) additionally calls `ConceptMasteryRepository.record_attempt(...)` after `write_episodic_memory`, whenever `output.mastery_update` is not `None`.

**Constraints:**
- This modifies `quinn.py` (previously shipped, 10 passing tests) — the existing 10 tests must still pass unchanged after this change (no behavioral regression to handoff logic, distractor analysis, etc.), verified explicitly (AC8).

### FR5: Live `AgentInput` Assembly

**Behavior:**
- A new function composes a real `AgentInput` for a turn: `student_profile` from `StudentProfileRepository`, `episodic_context` from `EpisodicMemoryRepository.recent_for_student`, `retrieved_chunks` from `DomainContentRepository.search` — then calls `nexus-supervisor`'s `assemble_agent_input(...)` with these real values instead of fixtures.
- `session_history` is assembled from an **in-process, per-session in-memory list** (a simple dict keyed by `session_id`), **not** the database — `core-data-schema` has no table for individual message transcripts (only aggregate `agent_sessions` and summarized `episodic_memory`). This is a genuine schema gap, not a design choice; see Gaps & Assumptions.

### FR6: Naive RAG Fallback (No Embedding Model Available)

**Behavior:**
- `DomainContentRepository.search()` shall use `ILIKE`/basic text matching against `domain_content.content` for this change — **not** real pgvector cosine-similarity search, since no embedding model/API key is available in this environment to embed the query text (see epic Requirements Discovery).
- The method signature and return type (`list[ContentChunk]`) are designed so a real vector-similarity implementation can replace the query internals later without changing any caller.

## Acceptance Criteria

- [ ] **AC1:** Given `AgentSessionRepository`, when `create_session` then `increment_turn_count` are called against a local Postgres instance, then `agent_sessions.turn_count` reflects the increment.
- [ ] **AC2:** Given `EpisodicMemoryRepository.write(...)`, when followed by `recent_for_student(...)`, then the written row round-trips correctly; given a second tenant, then it sees none of the first tenant's rows.
- [ ] **AC3:** Given a real `student_profiles` row, when `StudentProfileRepository.load_profile(...)` is called, then it returns a `StudentProfile` matching that row's values.
- [ ] **AC4:** Given `domain_content` rows, when `DomainContentRepository.search(...)` is called with a query matching one row's content, then that row is returned as a `ContentChunk`.
- [ ] **AC5:** Given `PersistentAgent` wrapping a real `Aria()` instance, when `.stream(input)` is run to completion, then a real `episodic_memory` row is written, **and** the streamed `AgentOutput`s are identical to calling the unwrapped `Aria()` directly on the same input (proving the wrapper changes nothing about agent behavior).
- [ ] **AC6:** Given `QuinnPersistentAgent` and a correct answer evaluation, when `.stream(input)` completes, then `concept_mastery.ease_factor` increased (capped at 3.0) and `review_count` incremented; given an incorrect answer, then `ease_factor` decreased (floored at 1.3).
- [ ] **AC7:** Given two different tenants' data in the same tables, when any repository method is called under one tenant's context, then it never returns the other tenant's rows.
- [ ] **AC8:** Given the full existing test suite (ARIA/MIRA/QUINN's 32 tests, `litellm-gateway`'s and `nexus-supervisor`'s and `langgraph-state-machine`'s tests), when re-run after this change (including QUINN's FR4 modification), then all still pass unchanged.

## Technical Design

### Architecture

```
apps/backend/db/
├── pool.py                  # asyncpg pool from DSN env var
├── tenant_scope.py          # tenant_scoped() context manager
├── repositories.py          # AgentSession/EpisodicMemory/StudentProfile/DomainContent/ConceptMastery repos
└── agent_persistence.py     # PersistentAgent, QuinnPersistentAgent
```

## Gaps & Assumptions

- **No `messages` table exists.** `AgentInput.session_history` (a list of raw per-turn `Message`s) has no durable backing store in `core-data-schema`'s schema — only aggregate `agent_sessions` (turn_count, session_notes) and summarized `episodic_memory` exist. This change assembles `session_history` from an in-process dict, which is lost on server restart. A real fix requires a new migration (a `messages` table) — tracked as an Open Question, out of scope here.
- **No embedding model available.** `DomainContentRepository.search()` uses text matching, not real vector similarity, until an embedding API is wired up (needs real credentials, out of scope per epic Requirements Discovery). **Discovered during implementation:** the fallback uses Postgres full-text search (`plainto_tsquery`), which ANDs every query term — a full natural-language question rarely matches a single-topic content row. This is a real, expected limitation of a non-semantic fallback, not a bug; a caller (`sse-endpoint`, eventually) may need to extract keywords rather than pass a raw question through.
- **`ease_factor`/`MasteryDelta.stability` field-name mismatch** — same discrepancy already flagged in `core-data-schema`'s `concept-mastery` child; not resolved here, just wired through consistently.
- **`StudentProfile` contract doesn't match `student_profiles`' actual columns.** Discovered during implementation: `StudentProfile` (`userId`, `displayName`, `createdAt`) predates `core-data-schema`, which built `student_profiles` from your literal spec (`test_date`, `score_goal`, `current_score`, `study_streak`) without cross-referencing it — there is no `displayName` column at all, and none of the learning-state columns are exposed anywhere in `AgentInput`. `StudentProfileRepository.load_profile()` sources `displayName` via a join to the pre-existing Stripe-starter `users.full_name` (falling back to `"Student"`); the learning-state columns aren't surfaced to agents at all in this change (see Open Questions).
- **`auth.uid() = student_id` RLS policies don't resolve for backend-originated writes.** Discovered during implementation: `core-data-schema`'s RLS policies were written assuming client-originated (PostgREST/JWT-authenticated) requests, where `auth.uid()` resolves automatically from the JWT. A raw backend connection has no JWT at all — `auth.uid()` would be `NULL` and every policy would deny. Resolved via `nexus.tenant_context.set_acting_user()` (new, alongside `set_tenant_context`), which sets the same `request.jwt.claim.sub` GUC PostgREST would — the backend "acts as" the student it's processing a turn for, for the duration of that scoped transaction. No new RLS policies were needed. `db.tenant_scope.tenant_scoped()` takes an optional `acting_user_id` accordingly, and `AgentSessionRepository.increment_turn_count()`'s signature gained a required `student_id` parameter it didn't have in the original sketch (FR2).
- **`concept_mastery.concept_id`'s domain-prefix check constraint** (`'%::%'`, from `core-data-schema`) doesn't match QUINN's own internal concept tracking, which was never prefixed (no `concept_mastery` table existed when QUINN was built). Fixed at the DB-write boundary only: `quinn.py` prefixes `MasteryDelta.conceptId` with `input.tenant_id` right before constructing it, while its student-facing response text and internal pending-question marker stay unprefixed (a raw `"mcat::"` string has no business appearing in something a student reads).
- **Testing methodology:** the connecting Postgres role (`bennguyen`, the local install's default) is a superuser, and superusers bypass RLS unconditionally — same discovery as `core-data-schema`'s own tests. A dedicated non-superuser role (`app_backend`) was created for every repository-under-test call; a separate superuser connection (`seed_conn`) is used only for test setup/verification (inserting `auth.users` rows, reading back final state), mirroring the arrange/act/assert split already used in `core-data-schema`'s verification.
- The Stripe starter's `handle_new_user()` trigger (from `apps/web/supabase/migrations/20230530034630_init.sql`) references `auth.users.raw_user_meta_data`, a column the local stub `auth.users` table didn't originally have — added during implementation. Once added, the trigger fires for real and auto-creates a `users` row on every `auth.users` insert, which test setup code needs to account for (update, not insert).

## Open Questions

- [ ] Should a `messages` table be added to the schema (a follow-up to `core-data-schema`) so `session_history` survives process restarts, rather than living only in-process?
- [ ] When real embeddings become available, should `DomainContentRepository.search()`'s interface stay the same (just swap the query internals), or does the caller need to change too?
- [ ] Should `StudentProfile` be extended with `test_date`/`score_goal`/`current_score`/`study_streak` (a coordinated change to `packages/core`'s TypeScript type and this Python mirror), so agents can actually use a student's real learning state instead of only `episodic_context` mention counts?

## Testing Strategy

### Integration Tests (local Postgres — reusing `core-data-schema`'s 7 migrations)

| Test Case | Expected Behavior |
|-----------|--------------------|
| `create_session` + `increment_turn_count` | `turn_count` reflects increment (AC1) |
| `write` + `recent_for_student`, two tenants | Round-trips correctly, tenant-isolated (AC2) |
| `load_profile` against a seeded row | Matches (AC3) |
| `search` with a matching query | Returns the matching chunk (AC4) |
| `PersistentAgent` wrapping real `Aria()` | Real DB write + identical output to unwrapped (AC5) |
| `QuinnPersistentAgent`, correct/incorrect answers | `ease_factor` adjusts correctly (AC6) |
| Cross-tenant queries | Zero rows returned (AC7) |
| Full existing suite re-run | All pass, including QUINN's 10 (AC8) |

## Dependencies

### Internal Dependencies

| Component | Reason |
|-----------|--------|
| `nexus-supervisor` | `assemble_agent_input`, `set_tenant_context` |
| `core-data-schema` | All 7 tables this change queries/writes |
| ARIA, MIRA, QUINN | Wrapped by `PersistentAgent`/`QuinnPersistentAgent` |

### External Dependencies

| Library | Reason |
|---------|--------|
| `asyncpg` | Direct Postgres access (not `supabase-py`/PostgREST — see epic Cross-Cutting Concerns) |

## Out of Scope

- A `messages` table / real `session_history` persistence — flagged as an Open Question, not built here.
- Real pgvector similarity search — text-matching fallback only.
- Real FSRS-5 (`stability`/`difficulty`) scheduling — simplified `ease_factor` heuristic only.
- Connecting to real hosted Supabase — local Postgres only (epic Requirements Discovery).

## References

- `changes/2026/07/17/nexus-orchestration/SPEC.md` — parent epic
- `changes/2026/07/16/core-data-schema/` — the schema this wires against
- `changes/2026/07/15/quinn-agent/SPEC.md` — QUINN's existing pending-marker mechanism this extends
