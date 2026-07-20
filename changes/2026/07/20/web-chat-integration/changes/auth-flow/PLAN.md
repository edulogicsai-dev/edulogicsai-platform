---
title: Auth Flow - Implementation Plan
change: auth-flow
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-20
sdd_version: 7.3.0
---

## Overview

Implementation plan for: Auth Flow

Specification: [SPEC.md](./SPEC.md)

## Phases

### Phase 1: Session & Profile Helpers

- `utils/supabase/profile.ts`: `getStudentProfile(supabase, userId, tenantId)`, `createStudentProfile(supabase, {userId, tenantId, testDate, scoreGoal})`, `getAccessToken(supabase)`.
- `NEXT_PUBLIC_DOMAIN_ID="mcat"` added to `.env.local.example`.

**Agent:** frontend-dev (fs-ts techpack)

### Phase 2: Post-Auth Routing Gate

- Extend `middleware.ts` / `utils/supabase/middleware.ts` to protect `/dashboard` and `/onboarding`.
- Wire signup/login success paths to check `getStudentProfile()` and route to `/onboarding` or `/dashboard` (FR2).

**Agent:** frontend-dev (fs-ts techpack)

### Phase 3: Onboarding Form + Placeholder Dashboard

- `app/onboarding/page.tsx` + `components/ui/OnboardingForm/OnboardingForm.tsx` (test_date, score_goal, submit → `createStudentProfile` → redirect).
- `app/dashboard/page.tsx` minimal placeholder (replaced by `dashboard-layout`).

**Agent:** frontend-dev (fs-ts techpack)

### Phase 4: Test & Review

- Integration tests per SPEC.md Testing Strategy against a local Supabase instance (real RLS).
- Manual verification in dev server per CLAUDE.md UI-change rule.

**Agent:** tester (fs-ts techpack) / reviewer (fs-ts techpack)

## Progress Tracking

- [ ] Phase 1: Session & Profile Helpers
- [ ] Phase 2: Post-Auth Routing Gate
- [ ] Phase 3: Onboarding Form + Placeholder Dashboard
- [ ] Phase 4: Test & Review

## Resource Usage

| Phase | Tokens (Input) | Tokens (Output) | Turns | Duration | Notes |
|-------|----------------|------------------|-------|----------|-------|
| 1 | - | - | - | | |
| 2 | - | - | - | | |
| 3 | - | - | - | | |
| 4 | - | - | - | | |
| **Total** | **-** | **-** | **-** | **-** | |
