---
title: Web Chat Integration - Implementation Plan
change: web-chat-integration
type: epic
spec: ./SPEC.md
status: draft
created: 2026-07-20
sdd_version: 7.3.0
---

## Overview

Implementation plan for epic: Web Chat Integration

Specification: [SPEC.md](./SPEC.md)

## Change Order

| # | Change | Description | Dependencies | Status |
|---|--------|-------------|--------------|--------|
| 1 | [auth-flow](./changes/auth-flow/PLAN.md) | Supabase Auth, student_profiles bootstrap, onboarding, redirect | None | pending |
| 2 | [sse-chat-hook](./changes/sse-chat-hook/PLAN.md) | `useAgentStream()` hook — fetch-based SSE parsing | auth-flow | pending |
| 3 | [chat-ui](./changes/chat-ui/PLAN.md) | Chat interface consuming the hook | sse-chat-hook | pending |
| 4 | [dashboard-layout](./changes/dashboard-layout/PLAN.md) | /dashboard shell hosting chat-ui | auth-flow, chat-ui | pending |

## Dependency Graph

```
auth-flow
    └──► sse-chat-hook
              └──► chat-ui
                        └──► dashboard-layout
```

Strictly linear, matching the user-specified order: each change is the direct prerequisite for the next (auth produces the JWT the hook needs; the hook is what chat-ui renders; chat-ui is what dashboard-layout hosts).

## PR Strategy

One PR per child change. Branch naming: `epic/web-chat-integration/<change-name>`.

## Verification Approach

- `auth-flow`: exercised against a local Supabase instance (`supabase start`) — real signup/login/session flow, real `student_profiles` insert under RLS (not mocked), since this is a client-side Supabase JS integration, not a backend unit.
- `sse-chat-hook`: unit-tested with a mocked `fetch` returning a canned SSE byte stream (including a mid-stream `agent_id` change, to exercise handoff detection) — no live backend call required for the hook's own parsing logic.
- `chat-ui` / `dashboard-layout`: component-level tests (React Testing Library) against the hook's return shape; manual verification in a running dev server per CLAUDE.md's UI-change rule ("start the dev server and use the feature in a browser before reporting complete").
- End-to-end (all 4 together): manual verification against a locally-running `apps/backend` (`JWT_SECRET`/`DATABASE_URL` set, per `nexus-orchestration`'s conditional router mount) + local Supabase, since no automated E2E harness exists in this repo yet.

## Progress Tracking

- [ ] Change 1: auth-flow
- [ ] Change 2: sse-chat-hook
- [ ] Change 3: chat-ui
- [ ] Change 4: dashboard-layout

## Resource Usage

| Change | Tokens (Input) | Tokens (Output) | Turns | Duration | Notes |
|--------|----------------|------------------|-------|----------|-------|
| auth-flow | - | - | - | | |
| sse-chat-hook | - | - | - | | |
| chat-ui | - | - | - | | |
| dashboard-layout | - | - | - | | |
| **Total** | **-** | **-** | **-** | **-** | |
