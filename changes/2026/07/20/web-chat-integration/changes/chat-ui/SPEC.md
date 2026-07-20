---
title: Chat UI
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

The chat interface itself: agent/user bubbles, avatars, a message input with quick-action pills, a streaming indicator, and seamless handoff transitions — the visual consumer of `useAgentStream()` (`sse-chat-hook`).

### Background

`sse-chat-hook` produces `{ messages, streaming, activeAgentId, send }` with no rendering. This change is purely presentational: turn that state into the conversation surface a student actually looks at.

### Current State

No chat rendering exists in `apps/web`. Tailwind + shadcn/ui (`components.json`, `tailwindcss-animate`) are configured but no chat-specific components exist.

---

## Functional Requirements

### FR1: Agent Bubble Rendering

**Behavior:**
- For each `ChatMessage` with `role: 'agent'`, render a left-aligned bubble with a colored left border using `var(--agent-{agent_id})` (CSS var — defined by `dashboard-layout`'s theme injection; this change only *references* the var, does not define its value, so it degrades gracefully — default border color — if rendered standalone before that child lands).
- Show an avatar (emoji/icon) + display name from `apps/web/lib/agent-registry.ts` (`{ aria: {name: 'ARIA', emoji: '🧭'}, mira: {name: 'MIRA', emoji: '💙'}, quinn: {name: 'QUINN', emoji: '📝'} }`) — a single shared file, not a chat-ui-local one, because `dashboard-layout`'s agent roster strip must render the exact same names/avatars (see epic Cross-Cutting Concerns on the lack of a backend agent-metadata endpoint, and Technical Design below on why this lives outside both consuming components). An unrecognized `agent_id` (future agent) falls back to a generic avatar + the raw `agent_id` string as the name, not a crash.
- Render `response` (plain text; `AgentOutput.response` is not markdown/HTML per any spec seen so far — rendered as text, not `dangerouslySetInnerHTML`).

### FR2: User Bubble Rendering

**Behavior:**
- For each `ChatMessage` with `role: 'user'`, render a right-aligned bubble in the brand/primary color (Tailwind `primary` token), no avatar.

### FR3: Error Rendering

**Behavior:**
- For `role: 'error'` entries (from `sse-chat-hook` FR2), render a distinct (non-agent, non-user) inline error banner within the message flow — visually distinguishable (e.g. destructive/red styling) so a student doesn't mistake a connection error for an agent's response.

### FR4: Message Input & Quick Actions

**Behavior:**
- A text input + send button pinned below the message list; `Enter` submits (Shift+Enter for newline), calling `send(message)` from the hook.
- The input and send button are disabled while `streaming === true` (prevents overlapping sends into a single hook instance — `sse-chat-hook` has no request-queueing).
- Three quick-action pills above/near the input: "Explain a concept", "Practice question", "Update my plan" — clicking one calls `send()` with that exact string as the message (no separate intent-classification path; NEXUS's existing intent classification, per `nexus-supervisor`, handles it same as free text).

### FR5: Streaming Indicator

**Behavior:**
- While `streaming === true` and no new agent bubble has yet appeared for the in-flight request, show a lightweight "thinking" indicator (e.g. animated dots) in the position the next bubble will occupy.
- Per the epic's Cross-Cutting Concerns (no token-level streaming — one SSE event per agent hop), this is a *between-events* indicator, not a per-token typewriter effect — it disappears the instant each `event: message` bubble is appended, and reappears only if another hop follows before `done`.

### FR6: Handoff Transitions

**Behavior:**
- When `activeAgentId` changes mid-conversation (a new agent bubble follows a different-agent bubble within the same `send()` cascade), the new agent's bubble simply appends to the message list in its normal position — no page reload, no separate "handoff" UI chrome inserted between them. "Seamless" here means the existing bubble-append behavior; no additional animation/callout beyond what FR1 already renders (each bubble already carries its own agent color/name, which is what makes the change visible).

## Acceptance Criteria

- [ ] **AC1:** Given the hook returns 2 agent messages with different `agent_id`s from one `send()` call, when rendered, then 2 distinctly-colored/avatared bubbles appear in order, with no reload or intermediate loading screen between them.
- [ ] **AC2:** Given `streaming === true`, when rendered, then the input and send button are disabled and a thinking indicator is visible; given `streaming === false`, then both are enabled and no indicator shows.
- [ ] **AC3:** Given a `role: 'error'` message, when rendered, then it is visually distinct from both agent and user bubbles (not just plain text in an agent-colored bubble).
- [ ] **AC4:** Given a click on the "Practice question" pill, when clicked, then `send('Practice question' | equivalent exact string)` is called with no separate text-entry step required.
- [ ] **AC5:** Given an `agent_id` not in the local registry (e.g. a future `sage`), when rendered, then a fallback avatar/name is shown, not a crash or blank bubble.
- [ ] **AC6:** Given the user presses Enter in the input with a non-empty message, when pressed, then `send()` is called and the input clears; given Shift+Enter, then a newline is inserted and `send()` is not called.

## Technical Design

### Architecture

```
apps/web/
├── lib/
│   └── agent-registry.ts     # id -> {name, emoji} — shared with dashboard-layout, lives outside components/ui/Chat so neither side "owns" it
└── components/ui/Chat/
    ├── ChatContainer.tsx     # wires useAgentStream(), owns layout
    ├── AgentBubble.tsx
    ├── UserBubble.tsx
    ├── ErrorBanner.tsx
    ├── MessageInput.tsx
    ├── QuickActionPills.tsx
    └── StreamingIndicator.tsx
```

### Component Data Flow

```
ChatContainer
  ├─ useAgentStream() → { messages, streaming, activeAgentId, send }
  ├─ messages.map(m => role==='agent' ? <AgentBubble/> : role==='user' ? <UserBubble/> : <ErrorBanner/>)
  ├─ streaming && <StreamingIndicator/>
  ├─ <QuickActionPills onSelect={send}/>
  └─ <MessageInput onSubmit={send} disabled={streaming}/>
```

## Gaps & Assumptions

- **Quick-action pill strings are sent as literal user messages**, relying entirely on NEXUS's existing free-text intent classification (`nexus-supervisor`) rather than a structured "intent" field in `ChatRequest` (which doesn't exist — `ChatRequest` only has `message`/`session_id`/`tenant_id`). If NEXUS's classifier doesn't route these three exact phrases usefully, that's a prompt/classification tuning issue on the backend, out of scope for this frontend change.
- **`AgentOutput.response` assumed plain text.** No spec reviewed (ARIA/MIRA/QUINN/sse-endpoint) indicates markdown or HTML content — rendered as plain text. If a future agent emits markdown, a rendering upgrade is a separate change.
- **No message persistence/history-on-reload** — `messages` lives only in the hook's in-memory state; refreshing `/dashboard` starts a new conversation (session continuity itself is already flagged as an open question in `sse-chat-hook`). Out of scope here.

## Testing Strategy

### Component Tests (React Testing Library, mocked `useAgentStream`)

| Test Case | Expected Behavior |
|-----------|--------------------|
| Two-agent-message hook state | 2 distinct bubbles in order (AC1) |
| `streaming: true` vs `false` | Input/button disabled + indicator shown, or not (AC2) |
| `role: 'error'` entry | Distinct error styling (AC3) |
| Click "Practice question" pill | `send()` called with exact expected string (AC4) |
| Unknown `agent_id` | Fallback avatar/name, no crash (AC5) |
| Enter vs. Shift+Enter in input | Submit vs. newline (AC6) |

## Dependencies

### Internal Dependencies

| Component | Reason |
|-----------|--------|
| `sse-chat-hook` | `useAgentStream()` — sole data source |
| `dashboard-layout` | Defines `--agent-{id}` CSS var *values* this change references (not blocking — degrades gracefully per FR1); both changes import the same `lib/agent-registry.ts` for names/avatars |

### External Dependencies

| Library | Reason |
|---------|--------|
| shadcn/ui primitives (existing, `components.json`) | Button/Input base components |

## Out of Scope

- Markdown/rich-text rendering of agent responses (see Gaps & Assumptions).
- Message persistence across page reloads.
- Per-token typewriter animation (backend doesn't stream at token granularity).
- The `--agent-{id}` CSS var *values* themselves — defined in `dashboard-layout`, referenced here only.

## References

- `changes/2026/07/20/web-chat-integration/SPEC.md` — parent epic (agent-metadata registry rationale)
- `changes/2026/07/20/web-chat-integration/changes/sse-chat-hook/SPEC.md` — `useAgentStream()` contract this change consumes
- `packages/core/src/agent/agent-output.ts` — `AgentOutput` fields available for rendering
