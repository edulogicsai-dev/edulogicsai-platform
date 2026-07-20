---
title: Dashboard Layout - Implementation Plan
change: dashboard-layout
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-20
sdd_version: 7.3.0
---

## Overview

Implementation plan for: Dashboard Layout

Specification: [SPEC.md](./SPEC.md)

## Phases

### Phase 1: Theme + Sidebar

- `theme/mcatTheme.ts` (FR1), `Sidebar.tsx` with name/countdown/progress (FR2), null-`current_score` handling.

**Agent:** frontend-dev (fs-ts techpack)

### Phase 2: Roster Strip + Chat Mount + Responsiveness

- `AgentRosterStrip.tsx` importing the shared `apps/web/lib/agent-registry.ts` (FR3), mount `ChatContainer` in `app/dashboard/page.tsx` (FR4), mobile collapse behavior (FR5).

**Agent:** frontend-dev (fs-ts techpack)

### Phase 3: Test & Review

- Component tests per SPEC.md Testing Strategy, including the AC5 color-parity check between `AgentRosterStrip` and `chat-ui`'s `AgentBubble`.
- Manual verification in dev server per CLAUDE.md UI-change rule — full flow: signup → onboarding → dashboard → send message → see streamed reply, at both desktop and mobile widths.

**Agent:** tester (fs-ts techpack) / reviewer (fs-ts techpack)

## Progress Tracking

- [ ] Phase 1: Theme + Sidebar
- [ ] Phase 2: Roster Strip + Chat Mount + Responsiveness
- [ ] Phase 3: Test & Review

## Resource Usage

| Phase | Tokens (Input) | Tokens (Output) | Turns | Duration | Notes |
|-------|----------------|------------------|-------|----------|-------|
| 1 | - | - | - | | |
| 2 | - | - | - | | |
| 3 | - | - | - | | |
| **Total** | **-** | **-** | **-** | **-** | |
