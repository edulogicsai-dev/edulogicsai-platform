---
title: Dashboard Layout
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

The `/dashboard` shell: a left sidebar (logo, student name, test countdown, score/progress), an agent-roster strip, domain theme CSS var injection, and the main content area hosting `chat-ui`. This is the last child — it assembles everything the epic built.

### Background

`auth-flow` produces a minimal placeholder `/dashboard/page.tsx` (SPEC.md Out of Scope) specifically so this change has a route to replace. This change replaces that placeholder with the real layout and mounts `chat-ui` inside it.

### Current State

`/dashboard/page.tsx` is `auth-flow`'s placeholder — no sidebar, no theming, no agent roster.

---

## Functional Requirements

### FR1: Domain Theme Injection

**Behavior:**
- At the `/dashboard` layout root (`app/dashboard/layout.tsx`), inject a hardcoded `mcat` theme object (`Record<`--${string}`, string>`, matching the `ThemeVars` shape from `packages/core/src/domain/domain-config.ts`) as inline CSS custom properties (`style={{...}}` on the root layout element), including at minimum `--agent-aria`, `--agent-mira`, `--agent-quinn`, plus `--brand-primary`/other base theme tokens.
- Per the epic's Cross-Cutting Concerns, this is a local constant, not fetched from any `DomainConfig` API (none exists) — selected via `NEXT_PUBLIC_DOMAIN_ID` for structural readiness (a `switch`/lookup keyed on it) even though `'mcat'` is the only branch implemented.

### FR2: Sidebar

**Behavior:**
- Renders: MCATai logo (existing `components/icons/Logo.tsx`), the student's display name (from `student_profiles` join / Supabase user metadata — reuse `auth-flow`'s profile helpers), a test-date countdown (`test_date - today`, in days, from `student_profiles.test_date`), and a practice-score progress bar (`current_score / score_goal`, from `student_profiles`).
- If `current_score` is `null` (no practice attempts yet — `auth-flow`'s onboarding never sets it), the progress bar shows an empty/0 state, not `NaN` or a crash.

### FR3: Agent Roster Strip

**Behavior:**
- A horizontal row of pills above the chat area, one per agent in `apps/web/lib/agent-registry.ts` (the shared registry file — same import `chat-ui` uses, not redefined here), each colored via the same `--agent-{id}` var FR1 injects.
- The roster is presentational only in this change — clicking a pill has no behavior (no agent-switching UI; NEXUS decides handoffs server-side per CLAUDE.md's architecture rules, not the client).

### FR4: Main Area — Chat Mount

**Behavior:**
- The main content area renders `chat-ui`'s `ChatContainer` as the default (and, in this change, only) view.

### FR5: Mobile Responsiveness

**Behavior:**
- Below Tailwind's `md` breakpoint, the sidebar collapses to a toggleable drawer/hamburger (not permanently hidden — still reachable), and the chat area takes the full viewport width.

## Acceptance Criteria

- [ ] **AC1:** Given `/dashboard` loads for an onboarded student, when rendered, then the sidebar shows their name, a countdown in days to `test_date`, and a progress bar reflecting `current_score`/`score_goal`.
- [ ] **AC2:** Given `current_score` is `null` (fresh account), when the sidebar renders, then the progress bar shows an empty/0 state without throwing.
- [ ] **AC3:** Given the viewport is mobile-width, when `/dashboard` loads, then the sidebar is collapsed behind a toggle and the chat remains fully usable full-width.
- [ ] **AC4:** Given `/dashboard` loads, when inspected, then `--agent-aria`/`--agent-mira`/`--agent-quinn` (and base theme tokens) are present as computed CSS custom properties on the layout root.
- [ ] **AC5:** Given the agent roster strip renders, when compared to `chat-ui`'s bubble colors, then the same 3 agents use the same colors in both places (single source of truth, not two divergent hardcoded lists).
- [ ] **AC6:** Given a student sends a message from `/dashboard`, when the response streams in, then it renders via `chat-ui` in the main area with no additional wiring beyond mounting `ChatContainer`.

## Technical Design

### Architecture

```
apps/web/
├── app/dashboard/
│   ├── layout.tsx        # modified: theme injection, Sidebar + roster shell
│   └── page.tsx           # modified: replaces auth-flow's placeholder, mounts ChatContainer
├── components/ui/Dashboard/
│   ├── Sidebar.tsx
│   └── AgentRosterStrip.tsx   # imports apps/web/lib/agent-registry.ts (same file chat-ui uses)
└── lib/
    └── theme/mcatTheme.ts     # ThemeVars constant (FR1) — agent-registry.ts itself lives in lib/ too, added by chat-ui
```

### Layout Structure

```
<DashboardLayout>                 // theme vars injected here (FR1)
  <Sidebar/>                      // collapsible on mobile (FR5)
  <main>
    <AgentRosterStrip/>           // FR3, shares chat-ui's agentRegistry
    <ChatContainer/>              // FR4, from chat-ui
  </main>
</DashboardLayout>
```

### Single Source of Truth for Agent Colors (AC5)

`apps/web/lib/agent-registry.ts` (`{id: {name, emoji}}`, added by `chat-ui`) is imported here unmodified, not duplicated — this change only *adds* the CSS var color values (`mcatTheme.ts`), keyed by the same `agent_id`s, so `AgentRosterStrip` and `AgentBubble` (from `chat-ui`) necessarily render identical names/avatars/colors by construction (one shared file + one shared theme constant), not by keeping two lists in sync manually.

## Gaps & Assumptions

- **`ThemeVars` is a hardcoded local constant, not sourced from any API** (epic Cross-Cutting Concerns) — when GREai/DATai are added, this file (`mcatTheme.ts`) is the seam a future "fetch DomainConfig.theme from an API" change would replace; not built generically here since only one domain exists to theme.
- **No dark-mode-specific theme values** — `darkMode: ['class', '[data-theme="dark"]']` already exists in `tailwind.config.js` from the starter; this change's theme vars use the same values in light/dark unless a specific agent color is illegible in dark mode, in which case a `:root[data-theme="dark"]` override is added (not assumed necessary upfront).
- **Test countdown for a past `test_date`** (student's exam date already passed) shows a non-negative fallback (e.g. "Test day!" or 0), not a negative number — small UX handling, not spec'd as a separate FR since it's a display edge case of FR2, not new behavior.

## Testing Strategy

### Component Tests (React Testing Library)

| Test Case | Expected Behavior |
|-----------|--------------------|
| Onboarded student profile data | Sidebar shows name/countdown/progress (AC1) |
| `current_score: null` | Empty/0-state progress bar, no crash (AC2) |
| Mobile viewport (via matchMedia mock or container width) | Sidebar collapsed behind toggle (AC3) |
| Layout root computed styles | `--agent-*` vars present (AC4) |
| `AgentRosterStrip` vs. `chat-ui` `AgentBubble` for same `agent_id` | Same color value (AC5) |
| `ChatContainer` mounted in `/dashboard` | Renders without additional props/wiring (AC6) |

## Dependencies

### Internal Dependencies

| Component | Reason |
|-----------|--------|
| `auth-flow` | Student profile data (`getStudentProfile()`: test_date, score_goal, current_score; `getDisplayName()`: name, added in that spec's FR6, 2026-07-22), placeholder route this change replaces |
| `chat-ui` | `ChatContainer`; also the change that first adds the shared `lib/agent-registry.ts` this change imports |

### External Dependencies

None beyond existing Tailwind/shadcn setup.

## Out of Scope

- Fetching `DomainConfig.theme` from an API — hardcoded constant (see Gaps & Assumptions).
- Agent-roster pill click behavior / manual agent switching — handoffs are server-decided per CLAUDE.md.
- Any view other than chat as the main area (e.g. a separate "progress" or "practice" tab) — chat is the only view this epic builds.
- Editing sidebar data (name, test_date, score_goal) — read-only display; editing would be a settings/profile change.

## References

- `changes/2026/07/20/web-chat-integration/SPEC.md` — parent epic (theme/agent-registry rationale)
- `changes/2026/07/20/web-chat-integration/changes/auth-flow/SPEC.md` — student_profiles data this reads
- `changes/2026/07/20/web-chat-integration/changes/chat-ui/SPEC.md` — `ChatContainer`, `agentRegistry` reused here
- `packages/core/src/domain/domain-config.ts` — `ThemeVars` shape
