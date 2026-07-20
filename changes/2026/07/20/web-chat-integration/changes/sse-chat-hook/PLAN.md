---
title: SSE Chat Hook - Implementation Plan
change: sse-chat-hook
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-20
sdd_version: 7.3.0
---

## Overview

Implementation plan for: SSE Chat Hook

Specification: [SPEC.md](./SPEC.md)

## Phases

### Phase 1: SSE Parser + Request Construction

- `hooks/useAgentStream.ts`: `fetch`-based request construction (FR1), buffered SSE event parser (FR2).
- `NEXT_PUBLIC_API_URL` added to `.env.local.example`.

**Agent:** frontend-dev (fs-ts techpack)

### Phase 2: Hook State & Handoff Detection

- `messages`/`streaming`/`activeAgentId`/`send` state wiring (FR3), per-event `activeAgentId` updates (FR4).
- Always send `session_id: null` (a client-generated/reused ID is unsafe against the real backend — see SPEC.md Technical Design). Accepted launch gap, not blocking (explicit product decision). Add a `// TODO(session_id-echo): wire real backend-echoed session_id once sse-endpoint returns it — see SPEC.md Open Questions` comment at the `send()` call site.

**Agent:** frontend-dev (fs-ts techpack)

### Phase 3: Test & Review

- Unit tests per SPEC.md Testing Strategy (mocked fetch, chunk-boundary case, handoff case).
- Confirm Open Question (session_id echo gap) against a live local backend if available; file follow-up if turn-2 continuity fails.

**Agent:** tester (fs-ts techpack) / reviewer (fs-ts techpack)

## Progress Tracking

- [ ] Phase 1: SSE Parser + Request Construction
- [ ] Phase 2: Hook State & Handoff Detection
- [ ] Phase 3: Test & Review

## Resource Usage

| Phase | Tokens (Input) | Tokens (Output) | Turns | Duration | Notes |
|-------|----------------|------------------|-------|----------|-------|
| 1 | - | - | - | | |
| 2 | - | - | - | | |
| 3 | - | - | - | | |
| **Total** | **-** | **-** | **-** | **-** | |
