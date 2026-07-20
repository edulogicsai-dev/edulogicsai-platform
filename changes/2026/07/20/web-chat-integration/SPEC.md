---
title: Web Chat Integration
type: epic
status: active
domain: mcat
issue: TBD
created: 2026-07-20
updated: 2026-07-20
sdd_version: 7.3.0
affected_components: []
---

## Overview

Connect the Next.js web app (`apps/web`) — currently a Stripe/Supabase SaaS starter with no student-facing product surface — to the live `POST /api/chat` SSE endpoint built in `changes/2026/07/17/nexus-orchestration/changes/sse-endpoint/`. This is the first epic where a real student can sign up, log in, and have an actual conversation with ARIA/MIRA/QUINN through a browser.

### Background

`nexus-orchestration` shipped a fully working, JWT-authenticated, tenant-scoped SSE chat endpoint (70/70 backend tests passing) with no frontend consumer — explicitly out of scope on that epic ("Frontend (`apps/web`) integration with `/api/chat` — backend endpoint only"). `apps/web` itself is the unmodified Vercel Next.js Subscription Starter: Stripe billing + Supabase Auth scaffolding (`components/ui/AuthForms/*`, `utils/supabase/*`, `utils/auth-helpers/*`) with no `student_profiles` bootstrapping, no chat surface, and no domain theming. This epic is the wiring: real Supabase Auth producing a real JWT, a hook that turns that JWT + a message into a live SSE stream, a chat UI that renders it, and a dashboard shell that hosts it.

### Current State

- `apps/web` has working email/password signup, signin, and password-reset flows (`components/ui/AuthForms/`), a Supabase browser/server client (`utils/supabase/client.ts`, `utils/supabase/server.ts`), and session-refresh middleware (`utils/supabase/middleware.ts`) — but nothing beyond `/account` (billing) as a post-login destination.
- `student_profiles` (`apps/web/supabase/migrations/20260716000002_student_profiles.sql`) exists with RLS policies that already permit a signed-in user to `select`/`insert`/`update` their own row (`auth.uid() = user_id and tenant_id = current_tenant()`) — no backend endpoint is needed to create it (see auth-flow's Gaps & Assumptions).
- `POST /api/chat` (`apps/backend/api/chat.py`) accepts `{message, session_id?, tenant_id}` with `Authorization: Bearer <jwt>`, 401s on invalid JWT, 403s if no `student_profiles` row exists for `(user_id, tenant_id)`, and streams `event: message` (one per agent hop, not per-token) / `event: done` / `event: error` as `text/event-stream`. In the `nexus-orchestration` dev environment this was verified against a local test JWT secret, not a real Supabase-issued token (see Cross-Cutting Concerns).
- No `NEXT_PUBLIC_API_URL` or `NEXT_PUBLIC_DOMAIN_ID` env vars exist yet in `apps/web`.
- `AgentOutput` (`packages/core/src/agent/agent-output.ts`) carries `agent_id` only — no `displayName`/`emoji`/`color`. No endpoint exposes the agent roster or `DomainConfig.theme` to the frontend (`DomainConfig` is Python-side only per CLAUDE.md's monorepo structure).

---

## Changes

| Change | Description | Dependencies |
|--------|-------------|--------------|
| [auth-flow](./changes/auth-flow/SPEC.md) | Supabase Auth signup/login, `student_profiles` bootstrap, JWT retrieval, onboarding (test_date + score_goal), redirect to /dashboard | None |
| [sse-chat-hook](./changes/sse-chat-hook/SPEC.md) | `useAgentStream()` — POSTs to `/api/chat` with the Bearer JWT, manually parses the SSE stream, tracks messages/streaming/activeAgentId | auth-flow |
| [chat-ui](./changes/chat-ui/SPEC.md) | Chat interface consuming `useAgentStream()` — bubbles, avatars, quick actions, streaming indicator, handoff transitions | sse-chat-hook |
| [dashboard-layout](./changes/dashboard-layout/SPEC.md) | `/dashboard` shell — sidebar, agent roster pills, domain theme CSS vars, mobile responsive, hosts chat-ui | auth-flow, chat-ui |

## Acceptance Criteria

- [ ] **AC1:** Given all 4 child changes are merged, when a new student signs up, completes onboarding, and sends a message, then they see a streamed reply rendered in the chat UI without ever touching `/account` or any Stripe surface.
- [ ] **AC2:** Given a fresh signup with no prior `student_profiles` row, when the student's first message is sent, then no `403` occurs — the row was created during auth-flow's onboarding step, before the first `/api/chat` call.
- [ ] **AC3:** Given ARIA's frustration-handoff fixture input (same as `nexus-orchestration`'s AC2/AC5), when it fires through the real UI, then a new MIRA-colored bubble appears in the same conversation without a page reload or a visible seam.
- [ ] **AC4:** Given the app is viewed on a mobile-width viewport, when the dashboard loads, then the sidebar collapses and the chat remains fully usable.

## Cross-Cutting Concerns

- **Real JWT verification is a deploy-time config concern, not a code change:** `apps/backend`'s `JWTVerifier` (see `nexus-orchestration`) was built and tested against a local test secret — no real Supabase credentials existed in that environment. For this epic's flows to work against an actually-deployed backend, `apps/backend`'s `JWT_SECRET` env var must be set to the target Supabase project's JWT signing secret (Project Settings → API → JWT Secret, HS256). No child change in this epic modifies backend code to make this true; it's an environment/deployment prerequisite, called out here so it isn't silently assumed.
- **No agent-metadata endpoint exists:** `AgentOutput.agent_id` is the only identifier the backend sends — no `displayName`, emoji, or color. chat-ui and dashboard-layout both need per-agent display metadata (border color via `--agent-{id}`, name, icon). Both changes import one shared file, `apps/web/lib/agent-registry.ts` (`aria`/`mira`/`quinn` → name/emoji; `dashboard-layout`'s theme constant adds the color), added by `chat-ui` and consumed as-is by `dashboard-layout` — not two independently hardcoded lists. Out of scope: a `GET /api/agents` roster endpoint that would let this be domain-config-driven instead of hardcoded.
- **Domain theming is hardcoded, not `DomainConfig`-driven:** `DomainConfig.theme` (`packages/core/src/domain/domain-config.ts`) is a type only — no TypeScript-side `mcat` `DomainConfig` object is instantiated anywhere (CLAUDE.md: `domains/mcat/` is Python-side). `dashboard-layout` defines its own local `mcat` theme CSS var object. `NEXT_PUBLIC_DOMAIN_ID='mcat'` selects it but there is currently only one theme to select — multi-domain theming from a real `DomainConfig` source is future work (GREai/DATai), not this epic.
- **SSE over `fetch`, not `EventSource`:** the browser's native `EventSource` API cannot send `POST` bodies or custom `Authorization` headers, both of which `/api/chat` requires. `sse-chat-hook` reads and parses the stream manually via `fetch()` + `ReadableStream`. This is established once in that child and consumed as-is by chat-ui.

## Domain Updates

### Glossary Terms

No new terms — `Handoff`, `AgentOutput`, `DomainConfig`, `tenant_id` are all pre-existing (`specs/domain/glossary.md`). This epic is a consumer of those concepts, not a definer of new ones.

## Out of Scope

- Real Supabase JWT secret provisioning in any deployed backend environment (see Cross-Cutting Concerns) — config, not code.
- A `GET /api/agents` roster/domain-config endpoint — agent display metadata is hardcoded client-side for this epic.
- Token-level incremental rendering — the backend streams one event per agent hop (`nexus-orchestration` decision), not per-token; the chat UI's "streaming indicator" reflects that granularity, not a typewriter effect.
- OAuth sign-in (GitHub, etc.) — `OauthSignIn.tsx` exists in the starter but is disabled per `775145a fix: disable GitHub OAuth in Supabase config`; this epic uses email/password only.
- GREai/DATai theming or multi-domain routing — `NEXT_PUBLIC_DOMAIN_ID` is hardcoded to `'mcat'`.
- `apps/mobile` — web only.
- Stripe/billing surfaces (`/account`, pricing) — untouched, pre-existing starter functionality.

## Requirements Discovery

### Questions & Answers

| Step | Question | Answer |
|------|----------|--------|
| Scope | What are the child changes and their order? | User specified all 4 (auth-flow, sse-chat-hook, chat-ui, dashboard-layout) with full behavioral detail up front. |
| Scope | Where does tenant/domain identity come from? | Hardcoded `tenant_id='mcat'` via `NEXT_PUBLIC_DOMAIN_ID`, not multi-tenant selection UI. |

### User Feedback

- User provided the full 4-child breakdown, dependency order, and per-child behavior (auth mechanics, hook return shape, UI elements, layout regions) in the initial request — no follow-up clarification was needed beyond confirming the interpreted scope before creation.

## References

- `changes/2026/07/17/nexus-orchestration/changes/sse-endpoint/SPEC.md` — the `POST /api/chat` contract this epic's frontend consumes
- `changes/2026/07/16/core-data-schema/changes/student-profiles/SPEC.md` — `student_profiles` schema and RLS policies
- `packages/core/src/agent/agent-output.ts` — `AgentOutput` shape streamed over SSE
- `packages/core/src/domain/domain-config.ts` — `ThemeVars`/`DomainConfig` types (Python-side instantiation only)
- `apps/web/components/ui/AuthForms/` — existing starter auth forms this epic builds on
- `CLAUDE.md` — Tech Stack (Next.js 14, Tailwind, shadcn/ui), Architecture Rules (tenant_id scoping, SSE-only agent responses)
