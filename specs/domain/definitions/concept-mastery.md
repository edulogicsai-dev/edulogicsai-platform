# Concept Mastery

## Definition

`concept_mastery` (`apps/web/supabase/migrations/20260716000006_concept_mastery.sql`) tracks per-student, per-concept mastery with spaced-repetition scheduling fields. This resolves the "no per-concept mastery map" gap explicitly called out in ARIA's spec (`changes/2026/07/10/aria-agent/SPEC.md`): `StudentProfile` has no per-concept mastery field, so ARIA currently approximates mastery via `episodic_context` mention counts. This table is the real thing that heuristic stands in for (not yet wired up — schema only).

## Schema

```sql
create table concept_mastery (
  student_id uuid not null,
  tenant_id text not null references tenants(id),
  concept_id text not null check (concept_id like '%::%'),  -- 'mcat::enzyme_kinetics'
  ease_factor real not null default 2.5,
  next_review date,
  last_reviewed_at timestamptz,
  review_count int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (student_id, tenant_id, concept_id),
  foreign key (student_id, tenant_id) references student_profiles(user_id, tenant_id) on delete cascade
);
```

## RLS

Students can `select`/`insert`/`update` only their own mastery rows, scoped to tenant. No `delete` policy.

## Known Discrepancy — `ease_factor` vs. FSRS-5

`CLAUDE.md`'s tech stack specifies `ts-fsrs` (FSRS-5 algorithm), which schedules using `stability`/`difficulty`/`retrievability`, not an "ease factor" (that's SM-2 terminology). This table implements exactly what was requested (`ease_factor`, `next_review`) rather than substituting FSRS-5's actual parameter set. **Before any real scheduling logic is built against this table, it likely needs revision to add `stability`/`difficulty` columns matching `ts-fsrs`.**

## Related

- [`Student Profile`](./student-profile.md) — composite FK target.
- `changes/2026/07/10/aria-agent/SPEC.md` — the mention-count heuristic this table resolves.
