---
title: SSE Chat Hook
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

`useAgentStream()` — a React hook that POSTs a student's message to `/api/chat` with their Supabase JWT, manually parses the resulting SSE stream (native `EventSource` cannot do this — see Technical Design), and exposes `{ messages, streaming, activeAgentId, send }` for `chat-ui` to render.

### Background

`POST /api/chat` (`nexus-orchestration`/`sse-endpoint`) is fully built and tested backend-side but has no frontend consumer. This change is the single integration point between the two — every SSE-parsing concern (event framing, handoff detection, error handling) belongs here, once, rather than being duplicated in `chat-ui`.

### Current State

No `apps/web` code calls `/api/chat`. No `NEXT_PUBLIC_API_URL` env var exists.

---

## Functional Requirements

### FR1: Request Construction

**Behavior:**
- `send(message: string)` issues `fetch(`${NEXT_PUBLIC_API_URL}/api/chat`, { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ message, session_id, tenant_id: NEXT_PUBLIC_DOMAIN_ID }) })`.
- `token` is obtained per-call via `auth-flow`'s `getAccessToken()` (FR4 of that change) — never cached across calls, so a refreshed session token is always used.
- **`session_id` is always `null`, on every call, not just the first.** The backend never echoes a resolved `session_id` back (see Gaps & Assumptions), and — discovered while implementing this change — a client-generated ID cannot safely substitute: `AgentSessionRepository.create_session` generates the ID server-side via `RETURNING id`, so a client-supplied value on the *first* call would simply be ignored/never created; sending that same never-created ID on the *second* call takes `sse-endpoint`'s "existing session" branch, whose `increment_turn_count` runs an `UPDATE ... WHERE id = $1` against a row that doesn't exist — a silent no-op (turn count never actually increments, but the request proceeds as if it had) rather than a visible failure, which is worse than the request simply erroring. Always sending `null` avoids this: it's the only branch that's genuinely safe against the real backend today.

### FR2: SSE Stream Parsing

**Behavior:**
- Read `response.body` via `getReader()` in a loop, decode chunks with `TextDecoder`, and buffer until a full event (`\n\n`-terminated block) is available, per the wire format in `sse-endpoint/SPEC.md`:
  ```
  event: message
  data: {...AgentOutput json...}

  event: done
  data:

  event: error
  data: {"error": "..."}
  ```
- On `event: message`: `JSON.parse(data)` into an `AgentOutput` (imported from `@mcatai/core`), append to `messages`.
- On `event: done`: set `streaming = false`.
- On `event: error`: parse `{error: string}`, append a synthetic error entry to `messages` (`role: 'error'` — see Technical Design), set `streaming = false`.
- On a non-2xx HTTP response (401/403/422 — no stream body): set `streaming = false`, append a synthetic error entry with the status-appropriate message, do not attempt to read a body as SSE.

### FR3: State Shape

**Behavior:**
- `messages: ChatMessage[]` — ordered list combining the user's own sent messages and each received `AgentOutput`, tagged with a discriminant (`role: 'user' | 'agent' | 'error'`) so `chat-ui` can render each distinctly.
- `streaming: boolean` — `true` from the moment `send()` is called until `done`/`error`/a request-level failure.
- `activeAgentId: string | null` — the `agent_id` of the most recently received `event: message`. Updates *per event*, not just once per `send()` call — this is what makes a mid-stream handoff (FR4) visible to `chat-ui` as it happens.
- `send: (message: string) => void` — fire-and-track; does not return a promise the caller must await (state updates drive re-renders).

### FR4: Handoff Detection

**Behavior:**
- Since `run_turn` returns the full ordered cascade as consecutive `event: message` events (e.g. ARIA then MIRA), the hook shall update `activeAgentId` on every `message` event, not just the first — a caller diffing `activeAgentId` across renders can detect the exact turn a handoff occurred, and `chat-ui` renders each `AgentOutput` as its own bubble in arrival order (no client-side merging of consecutive same-agent or different-agent outputs).

## Acceptance Criteria

- [ ] **AC1:** Given `send('hello')` is called, when the mocked fetch resolves a single `event: message` + `event: done`, then `messages` contains 1 user entry + 1 agent entry, and `streaming` ends `false`.
- [ ] **AC2:** Given a mocked SSE stream with 2 `event: message` events (`agent_id: 'aria'` then `'mira'`), when consumed, then `activeAgentId` observably transitions `'aria'` → `'mira'` (assert via a spy/effect across the stream, not just the final value) and `messages` contains both agent outputs in order.
- [ ] **AC3:** Given a mocked stream that emits `event: error`, when consumed, then `messages` gets a `role: 'error'` entry with the server's message and `streaming` ends `false`.
- [ ] **AC4:** Given the fetch resolves with HTTP `401`, when `send()` is called, then no SSE parsing is attempted, `streaming` ends `false`, and an error entry is added.
- [ ] **AC5:** Given a chunk boundary splits a single SSE event across two `fetch` stream reads, when parsed, then the event is still correctly assembled (tests the buffering logic explicitly, not just whole-event chunks).
- [ ] **AC6:** Given a second `send()` call within the same hook instance, when it completes, then `session_id: null` was sent on both calls — not a reused client-generated ID (see Technical Design/Gaps & Assumptions on why that would be unsafe against the real backend).

## Technical Design

### Architecture

```
apps/web/
└── hooks/
    └── useAgentStream.ts    # new
```

### Why `fetch` + manual parsing, not `EventSource`

`EventSource` only supports `GET` requests with no custom headers — `/api/chat` requires `POST` (message body) and a custom `Authorization: Bearer` header. There is no standard browser API for authenticated POST-based SSE; manual parsing over a `fetch` `ReadableStream` is the only option, and is what this hook implements once for the whole epic.

### `ChatMessage` Shape

```typescript
type ChatMessage =
  | { role: 'user'; content: string; timestamp: string }
  | ({ role: 'agent'; timestamp: string } & AgentOutput)
  | { role: 'error'; content: string; timestamp: string };
```

### Hook Signature

```typescript
function useAgentStream(): {
  messages: ChatMessage[];
  streaming: boolean;
  activeAgentId: string | null;
  send: (message: string) => void;
};
```

## Gaps & Assumptions

- **No cross-message session continuity is achievable today — this is a real backend gap, not a frontend workaround decision.** `sse-endpoint`'s `ChatRequest`/response contract (`api/chat.py`) never returns the resolved `session_id` in the SSE stream. Without it: sending `null` every time is *safe* (always takes the "create new session" branch) but means every message is its own fresh `agent_sessions` row — no session-level continuity across a conversation. Generating a client-side ID and reusing it is *not* a viable workaround (see Technical Design) — it doesn't fail loudly, it silently corrupts turn-count tracking. Given those two options, this hook always sends `null`. Flagged as an Open Question rather than silently shipping the unsafe alternative.
- **Error-entry `role: 'error'` is a frontend-only concept** — not part of `AgentOutput`; `chat-ui` must handle it as a distinct render case, not assume every non-user message is a valid `AgentOutput`.
- **Accepted for launch, not blocking:** per explicit product decision, the `session_id`-echo gap above does not block this change or the epic. The hook ships always sending `null` (the safe behavior), and the implementation carries an inline `// TODO(session_id-echo):` comment at the `send()` call site pointing at this SPEC's Open Questions, so wiring real continuity is a scoped follow-up once `sse-endpoint` is amended to echo the resolved ID, not a rediscovery.

## Testing Strategy

### Unit Tests (mocked `fetch`, no live backend)

| Test Case | Expected Behavior |
|-----------|--------------------|
| Single message + done | 2 messages, streaming false (AC1) |
| Two-agent handoff stream | activeAgentId transitions observably, 2 ordered agent messages (AC2) |
| `event: error` stream | Error message entry, streaming false (AC3) |
| HTTP 401 response | No SSE parse attempt, error entry (AC4) |
| Event split across chunk boundary | Correctly buffered/assembled (AC5) |
| Two sequential `send()` calls | Same `session_id` on both requests (AC6) |

## Dependencies

### Internal Dependencies

| Component | Reason |
|-----------|--------|
| `auth-flow` | `getAccessToken()` for the Bearer token |
| `packages/core` (`AgentOutput` type) | Typed parsing of `event: message` payloads |

### External Dependencies

None beyond the browser `fetch`/`ReadableStream` APIs already available in Next.js 14's target browsers.

## Out of Scope

- Fixing the `session_id`-echo gap in `apps/backend` (see Gaps & Assumptions / Open Questions) — this is a frontend-only change; the backend contract is consumed as-is.
- Reconnection/retry logic on dropped connections — a failed stream surfaces as an error entry; no automatic retry.
- Rendering — this hook returns state only; `chat-ui` (next child) is the consumer.

## Open Questions

- [ ] Should `sse-endpoint` be amended (in a follow-up change, out of this epic) to echo the resolved `session_id` as the first SSE event, so multi-turn conversations can share one session? **Decision: accepted as a known launch gap, not blocking** — until resolved, this hook always sends `session_id: null` (AC6), meaning every message today starts a brand-new `agent_sessions` row server-side rather than continuing a conversation-level session. Marked with a `// TODO(session_id-echo):` comment at the implementation site (see Gaps & Assumptions) so wiring real continuity is a known, findable follow-up rather than a rediscovery. This does not break individual turns (ARIA/MIRA/etc. still respond correctly per message) — it only means session-scoped state (e.g. `turn_count`) doesn't accumulate across a conversation yet.

## References

- `changes/2026/07/20/web-chat-integration/SPEC.md` — parent epic
- `changes/2026/07/17/nexus-orchestration/changes/sse-endpoint/SPEC.md` — `/api/chat` contract, SSE event format
- `apps/backend/api/chat.py` — `ChatRequest`, session resolution logic (source of the Gaps & Assumptions finding)
- `packages/core/src/agent/agent-output.ts` — `AgentOutput` type
