---
title: Auth Flow
type: feature
status: active
domain: mcat
issue: TBD
created: 2026-07-20
updated: 2026-07-20
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
- `student_profiles` (`(user_id, tenant_id)` primary key; columns `test_date`, `score_goal`, `current_score`, `study_streak`) has RLS policies already permitting the authenticated user to `insert`/`select`/`update` their own row (`auth.uid() = user_id and tenant_id = current_tenant()`) — confirmed in `apps/web/supabase/migrations/20260716000002_student_profiles.sql`. **No new backend endpoint is required to create it** (see Gaps & Assumptions).
- No `/dashboard` route, no onboarding form, no `NEXT_PUBLIC_DOMAIN_ID` env var exist yet.

---

## Functional Requirements

### FR1: Signup / Login

**Behavior:**
- Reuse the existing `Signup.tsx` / `PasswordSignIn.tsx` forms and their server actions (`signUp`, `signInWithPassword` in `utils/auth-helpers/server.ts`) unmodified — no new auth mechanism.
- On successful signup or login, the Supabase client holds a session (JWT in `access_token`), available via `supabase.auth.getSession()`.

### FR2: Post-Auth Routing Gate

**Behavior:**
- After successful signup/login, the system shall check whether a `student_profiles` row exists for `(user.id, tenant_id='mcat')`.
- If it does not exist: redirect to `/onboarding` (new route).
- If it exists: redirect to `/dashboard` directly (returning user, e.g. a second login) — no re-onboarding.

### FR3: Onboarding — student_profiles Bootstrap

**Behavior:**
- `/onboarding` renders a form collecting `test_date` (date input) and `score_goal` (numeric input, MCAT score range 472–528).
- On submit, insert one `student_profiles` row via the Supabase client: `{ user_id: session.user.id, tenant_id: 'mcat', test_date, score_goal }` (`current_score`/`study_streak` left at column defaults — `null`/`0`).
- This insert relies on the existing RLS `insert` policy (`auth.uid() = user_id and tenant_id = current_tenant()`) — the request must run under the authenticated Supabase session (not the anon key alone) for `auth.uid()` to resolve, and `current_tenant()` must be set consistently with `tenant_id='mcat'` (see Gaps & Assumptions on `current_tenant()`).
- On successful insert: redirect to `/dashboard`.
- On insert failure (e.g. duplicate row from a race, RLS denial): show an inline error, do not redirect.

### FR4: Session → Bearer Token

**Behavior:**
- Expose a helper (`getAccessToken()`) that reads `supabase.auth.getSession()` and returns `session.access_token`, for use by `sse-chat-hook` as the `Authorization: Bearer <token>` value on `/api/chat` requests.
- The Supabase JS client auto-refreshes the session; callers should re-fetch the token per request rather than caching it, so a refreshed token is always used.

### FR5: Route Protection

**Behavior:**
- `/dashboard` and `/onboarding` shall require an authenticated session — an unauthenticated request redirects to `/signin`.
- Extend the existing `middleware.ts` matcher / `updateSession` check (already runs `supabase.auth.getUser()` on every non-static request) rather than adding a second auth mechanism.

## Acceptance Criteria

- [ ] **AC1:** Given a new user submits the signup form, when signup succeeds, then they land on `/onboarding`, not `/dashboard`.
- [ ] **AC2:** Given a user on `/onboarding` submits `test_date` and `score_goal`, when the submit completes, then a `student_profiles` row exists with those values and `tenant_id='mcat'`, and the user is redirected to `/dashboard`.
- [ ] **AC3:** Given a returning user (existing `student_profiles` row) logs in, when login succeeds, then they land directly on `/dashboard`, skipping onboarding.
- [ ] **AC4:** Given an unauthenticated visitor requests `/dashboard` or `/onboarding` directly, when the request is made, then they are redirected to `/signin`.
- [ ] **AC5:** Given an authenticated session, when `getAccessToken()` is called, then it returns a non-empty JWT string usable as a Bearer token.
- [ ] **AC6:** Given the onboarding insert fails (e.g. simulated RLS denial), when submit is clicked, then an inline error is shown and the user remains on `/onboarding`.

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
│   └── profile.ts            # new: getStudentProfile(), createStudentProfile(), getAccessToken()
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
- **`current_tenant()` resolution.** `student_profiles`' RLS policies check `tenant_id = current_tenant()` — `current_tenant()` is defined in the `core-data-schema` epic (`tenant-foundation` child) and is expected to resolve from a session claim/setting already established by that work. This change assumes `current_tenant()` correctly resolves to `'mcat'` for a signed-in user without additional per-request configuration; if it does not (e.g. requires an explicit `SET`), the onboarding insert will fail RLS and surface via AC6's error path rather than fail silently.
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
- `apps/web/supabase/migrations/20260716000002_student_profiles.sql` — table + RLS
- `apps/web/components/ui/AuthForms/`, `apps/web/utils/auth-helpers/` — existing forms/actions reused
