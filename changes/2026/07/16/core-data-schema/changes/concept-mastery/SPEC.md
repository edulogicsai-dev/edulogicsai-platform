---
title: Concept Mastery (Spaced Repetition)
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

A `concept_mastery` table tracking per-student, per-concept mastery with spaced-repetition scheduling fields, resolving the "no per-concept mastery map" gap explicitly called out in ARIA's spec (`changes/2026/07/10/aria-agent/SPEC.md` FR3/Gaps & Assumptions): `StudentProfile` has no per-concept mastery field, so ARIA approximates "has this concept been assessed" and "explanation depth" via `episodic_context` mention counts. This table is the real thing that heuristic stands in for.

### Current State

No per-concept mastery tracking exists anywhere. ARIA infers mastery from counting prior mentions in fixture `episodic_context` data; there is no durable, queryable mastery state.

---

## Functional Requirements

### FR1: `concept_mastery` Table

**Behavior:**
- Columns: `student_id uuid not null`, `tenant_id text not null references tenants(id)`, `concept_id text not null` (e.g. `'mcat::enzyme_kinetics'` — `<domain>::<slug>` convention per `specs/domain/glossary.md`), `ease_factor real not null default 2.5`, `next_review date`, `last_reviewed_at timestamptz`, `review_count int not null default 0`, `created_at timestamptz not null default now()`, `updated_at timestamptz not null default now()`.
- Primary key: `(student_id, tenant_id, concept_id)`.
- Composite foreign key `(student_id, tenant_id) references student_profiles(user_id, tenant_id) on delete cascade`.
- `concept_id` must contain the domain-prefix separator: `check (concept_id like '%::%')`.

**Constraints:**
- `next_review` is nullable — a concept not yet scheduled for review (e.g. never studied) has none.
- `ease_factor` defaults to `2.5` (a conventional starting point for ease-factor-based scheduling).

### FR2: RLS

**Behavior:**
- A student can `select`/`insert`/`update` only their own mastery rows, scoped to tenant. No `delete` policy.

## Acceptance Criteria

- [ ] **AC1:** Given a valid `student_profiles` row, when a `concept_mastery` row is inserted with `concept_id = 'mcat::enzyme_kinetics'`, then it succeeds.
- [ ] **AC2:** Given a `concept_id` without a `::` separator (e.g. `'enzyme_kinetics'`), when an insert is attempted, then it fails the check constraint.
- [ ] **AC3:** Given no matching `student_profiles` row, when an insert is attempted, then it fails the foreign key constraint.
- [ ] **AC4:** Given an insert without `ease_factor`, when inserted, then it defaults to `2.5`.
- [ ] **AC5:** Given two students, when one queries `concept_mastery` as an authenticated user, then RLS returns only their own rows.

## Technical Design

### Migration

`apps/web/supabase/migrations/<timestamp>_concept_mastery.sql`:

```sql
create table concept_mastery (
  student_id uuid not null,
  tenant_id text not null references tenants(id),
  concept_id text not null check (concept_id like '%::%'),
  ease_factor real not null default 2.5,
  next_review date,
  last_reviewed_at timestamptz,
  review_count int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (student_id, tenant_id, concept_id),
  foreign key (student_id, tenant_id) references student_profiles(user_id, tenant_id) on delete cascade
);

alter table concept_mastery enable row level security;

create policy "Students can view own mastery." on concept_mastery
  for select using (auth.uid() = student_id and tenant_id = current_tenant());

create policy "Students can insert own mastery." on concept_mastery
  for insert with check (auth.uid() = student_id and tenant_id = current_tenant());

create policy "Students can update own mastery." on concept_mastery
  for update using (auth.uid() = student_id and tenant_id = current_tenant());
```

## Specs Directory Changes

### Changes Summary

| Path | Action | Description |
|------|--------|--------------|
| specs/domain/definitions/concept-mastery.md | Create | The `concept_mastery` table and its relationship to ARIA's mention-count heuristic |

## Domain Updates

### Definition Specs

| File | Description | Action |
|------|-------------|--------|
| `concept-mastery.md` | `concept_mastery` table definition | create |

## Testing Strategy

### Integration Tests (Supabase local/CI)

| Test Case | Expected Behavior |
|-----------|--------------------|
| Insert with `concept_id = 'mcat::enzyme_kinetics'` | Succeeds |
| Insert with `concept_id = 'enzyme_kinetics'` (no `::`) | Check constraint violation |
| Insert with no matching `student_profiles` row | FK violation |
| Insert without `ease_factor` | Defaults to `2.5` |
| RLS: student queries mastery rows | Only own rows returned |

## Dependencies

### Internal Dependencies

| Component | Reason |
|-----------|--------|
| `tenant-foundation` | `tenants`, `current_tenant()` |
| `student-profiles` | Composite FK target |

## Out of Scope

- Wiring ARIA to actually read/write this table instead of its `episodic_context` mention-count heuristic — schema only.
- The actual FSRS-5 scheduling algorithm (`ts-fsrs`, per `CLAUDE.md`'s tech stack) — this table stores the fields, not the scheduling logic itself.
- A normalized `concepts` catalog table — `concept_id` stays free-text (see epic SPEC.md Out of Scope).

## Gaps & Assumptions

- **`ease_factor` is SM-2 terminology, not native FSRS.** `CLAUDE.md`'s tech stack specifies `ts-fsrs` (FSRS-5 algorithm), which schedules using `stability`/`difficulty`/`retrievability`, not an ease factor. This change implements exactly the fields requested (`next_review`, `ease_factor`) rather than substituting FSRS-5's actual parameter set unilaterally — but when `packages/memory`'s FSRS integration is actually wired up, this table will likely need `stability`/`difficulty` columns instead of (or alongside) `ease_factor` (see Open Questions).

## Open Questions

- [ ] Should this table be revised to use FSRS-5's actual `stability`/`difficulty`/`retrievability` fields instead of `ease_factor`, to match `ts-fsrs` (the library `CLAUDE.md` specifies), before any real scheduling logic is built against it?

## References

- `changes/2026/07/16/core-data-schema/SPEC.md` — parent epic
- `changes/2026/07/10/aria-agent/SPEC.md` — the mention-count heuristic this table resolves
- `specs/domain/glossary.md` — `concept_id` prefix convention
