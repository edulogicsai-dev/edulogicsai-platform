---
title: Auth Flow
type: feature
status: active
domain: mcat
issue: TBD
created: 2026-07-20
updated: 2026-07-22
sdd_version: 7.3.0
parent_epic: ../../SPEC.md
affected_components: []
---

## Overview

Email/password signup and login using the existing starter's Supabase Auth, followed by a one-time onboarding step that creates the student's `student_profiles` row and collects `test_date`/`score_goal`, ending at `/dashboard`. This is the first change in the epic — every other child depends on the authenticated session and tenant-membership row this change produces.

### Background

`apps/web`'s Supabase Auth scaffolding (`components/ui/AuthForms/*`, `utils/supabase/*`, `utils/auth-helpers/*`) already handles signup/login/session-refresh for the Stripe starter, but nothing downstream of login exists — no `student_profiles` bootstrap, no onboarding, no `/dashboard`. `POST /api/chat` (`sse-endpoint` FR3) returns `403` for any authenticated user without a `student_profiles` row for the request's `tenant_id` — that row must exist *before* the first chat message, not be created lazily by the backend.

### Current State

- Signup (`components/ui/AuthForms/Signup.tsx`) and signin (`PasswordSignIn.tsx`) exist and redirect to `/` on success (`utils/auth-helpers/settings.ts` / server actions in `utils/auth-helpers/server.ts`).
- `student_profiles` (`(user_id, tenant_id)` primary key; columns `test_date`, `score_goal`, `current_score`, `study_streak`) has RLS policies already permitting the authenticated user to `insert`/`select`/`update` their own row (`auth.uid() = user_id and tenant_id in (select id from tenants)` as of `20260722000001_student_profiles_tenant_membership_rls.sql` — see FR3's amendment) — confirmed in `apps/web/supabase/migrations/20260716000002_student_profiles.sql`. **No new backend endpoint is required to create it** (see Gaps & Assumptions).
- No `/dashboard` route, no onboarding form, no `NEXT_PUBLIC_DOMAIN_ID` env var exist yet.

---

## Functional Requirements

### FR1: Signup / Login

**Behavior:**
- Reuse the existing `Signup.tsx` / `PasswordSignIn.tsx` forms and their server actions (`signUp`, `signInWithPassword` in `utils/auth-helpers/server.ts`) — no new auth mechanism.
- On successful signup or login, the Supabase client holds a session (JWT in `access_token`), available via `supabase.auth.getSession()`.

**Amended 2026-07-22:** `Signup.tsx` was not left fully unmodified as originally stated — it now also collects `full_name` (required text input), passed as `options.data.full_name` to `supabase.auth.signUp()`. The Stripe starter's existing `handle_new_user()` trigger (`apps/web/supabase/migrations/20230530034630_init.sql`, pre-dates this epic) already reads `raw_user_meta_data->>'full_name'` into the `users` table on signup — this change just started populating that metadata field for the first time, no new trigger or table needed. Without this, `users.full_name` was null for every account (see FR-new below).

### FR2: Post-Auth Routing Gate

**Behavior:**
- After successful signup/login, the system shall check whether a `student_profiles` row exists for `(user.id, tenant_id='mcat')`.
- If it does not exist: redirect to `/onboarding` (new route).
- If it exists: redirect to `/dashboard` directly (returning user, e.g. a second login) — no re-onboarding.

### FR3: Onboarding — student_profiles Bootstrap

**Behavior:**
- `/onboarding` renders a form collecting `test_date` (date input) and `score_goal` (numeric input, MCAT score range 472–528).
- On submit, insert one `student_profiles` row via the Supabase client: `{ user_id: session.user.id, tenant_id: 'mcat', test_date, score_goal }` (`current_score`/`study_streak` left at column defaults — `null`/`0`).
- This insert relies on the existing RLS `insert` policy — the request must run under the authenticated Supabase session (not the anon key alone) for `auth.uid()` to resolve.
- On successful insert: redirect to `/dashboard`.
- On insert failure (e.g. duplicate row from a race, RLS denial): show an inline error, do not redirect.

**Amended 2026-07-22 — RLS policy fix:** originally `tenant_id = current_tenant()`, and this FR flagged (see Gaps & Assumptions, original text kept below) that the insert's success depended on `current_tenant()` resolving correctly. It didn't: Supabase Auth doesn't populate `app_metadata.tenant_id` by default and this project has no signup hook that sets it, so `current_tenant()` resolved to `null` for every real browser session, and the onboarding insert would have failed RLS for every single user — not the edge case FR3 originally hedged about, but the universal case. Fixed in `20260722000001_student_profiles_tenant_membership_rls.sql` (see `student-profiles/SPEC.md` FR2's amendment and `web-chat-integration/SPEC.md`'s epic-level note): policies now check `tenant_id in (select id from tenants)` instead, which this insert already naturally satisfies (`tenant_id: 'mcat'` is a real row in `tenants`).

**Amended 2026-07-22 — date validation:** `test_date` is submitted from an `<input type="date">`, which yields `''` (empty string) when the field hasn't been touched, not `null`/`undefined`. Postgres' `date` column rejects `''` outright (`invalid input syntax for type date: ""`) rather than treating it as absent, which surfaced as an unhandled insert failure before this fix. `createStudentProfile` (`utils/supabase/profile.ts`) now converts with `test_date: testDate || null` before the insert, so an empty string becomes a real SQL `null` (a valid value — the column is nullable) instead of an invalid one. The HTML input still has `required`, so this only matters if that client-side constraint is bypassed (direct API call, JS disabled, etc.) — defense in depth, not the primary validation layer.

### FR4: Session → Bearer Token

**Behavior:**
- Expose a helper (`getAccessToken()`) that reads `supabase.auth.getSession()` and returns `session.access_token`, for use by `sse-chat-hook` as the `Authorization: Bearer <token>` value on `/api/chat` requests.
- The Supabase JS client auto-refreshes the session; callers should re-fetch the token per request rather than caching it, so a refreshed token is always used.

### FR5: Route Protection

**Behavior:**
- `/dashboard` and `/onboarding` shall require an authenticated session — an unauthenticated request redirects to `/signin`.
- Extend the existing `middleware.ts` matcher / `updateSession` check (already runs `supabase.auth.getUser()` on every non-static request) rather than adding a second auth mechanism.

### FR6: Display Name (Added 2026-07-22)

**Behavior:**
- Expose a helper (`getDisplayName(supabase, userId)`) that reads `users.full_name` (the Stripe starter's pre-existing billing-identity table, not `student_profiles`) and returns it, falling back to the literal string `"Student"` if null.
- Consumed by `dashboard-layout`'s sidebar (`changes/2026/07/20/web-chat-integration/changes/dashboard-layout/SPEC.md`) to render the student's name — this change only exposes the helper, it doesn't render anything itself (no `/onboarding`/`/dashboard` placeholder page in this change shows a name).
- Mirrors `apps/backend`'s `StudentProfileRepository.load_profile`'s identical fallback (`db/repositories.py`: `displayName=row["full_name"] or "Student"`) — same convention on both sides of the stack, not a coincidence.

**Constraints:**
- Before FR1's amendment (full_name capture), this fallback fired for every single account, since `full_name` was always null. It now only fires for accounts that skip/bypass the (required) full-name field, or ones created before this change shipped.

## Acceptance Criteria

- [ ] **AC1:** Given a new user submits the signup form, when signup succeeds, then they land on `/onboarding`, not `/dashboard`.
- [ ] **AC2:** Given a user on `/onboarding` submits `test_date` and `score_goal`, when the submit completes, then a `student_profiles` row exists with those values and `tenant_id='mcat'`, and the user is redirected to `/dashboard`.
- [ ] **AC3:** Given a returning user (existing `student_profiles` row) logs in, when login succeeds, then they land directly on `/dashboard`, skipping onboarding.
- [ ] **AC4:** Given an unauthenticated visitor requests `/dashboard` or `/onboarding` directly, when the request is made, then they are redirected to `/signin`.
- [ ] **AC5:** Given an authenticated session, when `getAccessToken()` is called, then it returns a non-empty JWT string usable as a Bearer token.
- [ ] **AC6:** Given the onboarding insert fails (e.g. simulated RLS denial), when submit is clicked, then an inline error is shown and the user remains on `/onboarding`.
- [ ] **AC7 (Added 2026-07-22):** Given a user signs up with a full name, when `getDisplayName()` is called for that user, then it returns the submitted name; given `full_name` is null (pre-existing account or bypassed field), then it returns `"Student"`.
- [ ] **AC8 (Added 2026-07-22):** Given `test_date` is submitted as an empty string (field untouched, client-side `required` bypassed), when the onboarding insert runs, then it succeeds with `test_date = null` rather than failing on `invalid input syntax for type date`.

## Technical Design

### Architecture

```
apps/web/
├── app/
│   ├── onboarding/
│   │   └── page.tsx          # new: test_date + score_goal form
│   └── dashboard/
│       └── page.tsx          # new: placeholder until dashboard-layout child lands
├── components/ui/OnboardingForm/
│   └── OnboardingForm.tsx    # new
├── utils/supabase/
│   └── profile.ts            # new: getStudentProfile(), createStudentProfile(), getAccessToken(), getDisplayName() (FR6, added 2026-07-22)
└── middleware.ts              # modified: gate /dashboard, /onboarding
```

### Data Flow

```
Signup/Login (existing forms)
    → Supabase session established
    → check student_profiles row (getStudentProfile)
        ├─ exists    → redirect /dashboard
        └─ missing   → redirect /onboarding
                          → submit → insert student_profiles (RLS-checked)
                          → redirect /dashboard
```

### Environment

New env vars (`.env.local.example`):
```
NEXT_PUBLIC_DOMAIN_ID="mcat"
```
(`NEXT_PUBLIC_API_URL` is introduced by `sse-chat-hook`, not this change.)

## Gaps & Assumptions

- **No new backend endpoint for `student_profiles` creation.** The obvious reading of "create student_profiles row via backend" would be a new `POST /api/student-profiles` on `apps/backend`. That's unnecessary: the existing RLS `insert` policy already permits the authenticated user to create their own row directly via the Supabase client, and `apps/backend` has no student_profiles-*creation* code path today (`StudentProfileRepository.load_profile` in `db/repositories.py` only reads). Adding a backend endpoint would duplicate what RLS already enforces for no benefit. Flagged explicitly rather than silently reinterpreted.
- **`current_tenant()` resolution — superseded 2026-07-22, kept for history.** Original text: "`student_profiles`' RLS policies check `tenant_id = current_tenant()` — `current_tenant()` is defined in the `core-data-schema` epic (`tenant-foundation` child) and is expected to resolve from a session claim/setting already established by that work. This change assumes `current_tenant()` correctly resolves to `'mcat'` for a signed-in user without additional per-request configuration; if it does not (e.g. requires an explicit `SET`), the onboarding insert will fail RLS and surface via AC6's error path rather than fail silently." The assumption was wrong, not just untested — see FR3's 2026-07-22 amendment for what actually happened and the fix.
- **MCAT score range (472–528) is hardcoded** as the `score_goal` input's min/max — reasonable for the `mcat` domain this epic targets, not domain-configurable (consistent with the epic's "hardcoded theming/tenant" scope).
- **`/onboarding` is a full page, not a modal over `/dashboard`** — simpler routing/redirect logic, no assumption about `dashboard-layout` (a later child) existing yet.

## Testing Strategy

### Integration Tests (local Supabase instance, real RLS — not mocked)

| Test Case | Expected Behavior |
|-----------|--------------------|
| New signup → first login | Redirects to `/onboarding` (AC1) |
| Onboarding submit with valid data | `student_profiles` row created, redirect to `/dashboard` (AC2) |
| Second login (row already exists) | Redirects straight to `/dashboard` (AC3) |
| Unauthenticated `/dashboard` request | Redirect to `/signin` (AC4) |
| `getAccessToken()` after login | Returns non-empty JWT (AC5) |
| Onboarding insert forced to fail (wrong `tenant_id` bypassing RLS check) | Inline error, no redirect (AC6) |
| `getDisplayName()` with/without `full_name` set (Added 2026-07-22) | Returns the name, or `"Student"` fallback (AC7) |
| Onboarding submit with `test_date` forced to `''` (Added 2026-07-22) | Insert succeeds with `test_date = null`, not a Postgres date-syntax error (AC8) |

## Dependencies

### Internal Dependencies

| Component | Reason |
|-----------|--------|
| `student_profiles` migration (`core-data-schema`) | Table + RLS policies this change writes through |

### External Dependencies

| Library | Reason |
|---------|--------|
| `@supabase/ssr`, `@supabase/supabase-js` (existing) | Auth session, client-side insert |

## Out of Scope

- New backend endpoint for profile creation (see Gaps & Assumptions — RLS-direct insert is sufficient).
- OAuth signin (`OauthSignIn.tsx`) — disabled per `775145a`, email/password only.
- Editing `test_date`/`score_goal` after onboarding — no settings/profile-edit UI in this change.
- `dashboard-layout`'s actual sidebar/chat content — `/dashboard/page.tsx` here is a minimal placeholder the later child replaces.

## References

- `changes/2026/07/20/web-chat-integration/SPEC.md` — parent epic
- `changes/2026/07/17/nexus-orchestration/changes/sse-endpoint/SPEC.md` FR3 — the 403-on-no-membership check this change prevents
- `apps/web/supabase/migrations/20260716000002_student_profiles.sql` — table + original RLS
- `apps/web/supabase/migrations/20260722000001_student_profiles_tenant_membership_rls.sql` — RLS amendment (FR3, Added 2026-07-22)
- `apps/web/supabase/migrations/20230530034630_init.sql` — pre-existing `handle_new_user()` trigger FR1's `full_name` metadata now actually populates (Added 2026-07-22)
- `changes/2026/07/16/core-data-schema/changes/student-profiles/SPEC.md` — the amended RLS policy's canonical spec
- `apps/web/components/ui/AuthForms/`, `apps/web/utils/auth-helpers/` — existing forms/actions reused
