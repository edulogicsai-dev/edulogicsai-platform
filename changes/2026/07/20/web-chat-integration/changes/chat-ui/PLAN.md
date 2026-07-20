---
title: Chat UI - Implementation Plan
change: chat-ui
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-20
sdd_version: 7.3.0
---

## Overview

Implementation plan for: Chat UI

Specification: [SPEC.md](./SPEC.md)

## Phases

### Phase 1: Bubbles & Registry

- `lib/agent-registry.ts` (shared location — dashboard-layout imports the same file, not a duplicate), `AgentBubble.tsx`, `UserBubble.tsx`, `ErrorBanner.tsx` (FR1-FR3).

**Agent:** frontend-dev (fs-ts techpack)

### Phase 2: Input, Quick Actions, Streaming Indicator

- `MessageInput.tsx`, `QuickActionPills.tsx`, `StreamingIndicator.tsx` (FR4-FR5).
- `ChatContainer.tsx` wiring `useAgentStream()` to all subcomponents, handoff append behavior (FR6).

**Agent:** frontend-dev (fs-ts techpack)

### Phase 3: Test & Review

- Component tests per SPEC.md Testing Strategy (mocked hook).
- Manual verification in dev server per CLAUDE.md UI-change rule (golden path + unknown-agent fallback + streaming disabled state).

**Agent:** tester (fs-ts techpack) / reviewer (fs-ts techpack)

## Progress Tracking

- [ ] Phase 1: Bubbles & Registry
- [ ] Phase 2: Input, Quick Actions, Streaming Indicator
- [ ] Phase 3: Test & Review

## Resource Usage

| Phase | Tokens (Input) | Tokens (Output) | Turns | Duration | Notes |
|-------|----------------|------------------|-------|----------|-------|
| 1 | - | - | - | | |
| 2 | - | - | - | | |
| 3 | - | - | - | | |
| **Total** | **-** | **-** | **-** | **-** | |
