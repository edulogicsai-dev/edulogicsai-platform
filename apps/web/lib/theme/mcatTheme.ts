import type { ThemeVars } from '@mcatai/core';

// Hardcoded local constant, not sourced from any API -- packages/core's
// DomainConfig.theme has no TypeScript-side instantiation (domains/mcat is
// Python-side per CLAUDE.md). This is the seam a future
// "fetch DomainConfig.theme from an API" change would replace once
// GREai/DATai need real per-domain theming. See
// changes/2026/07/20/web-chat-integration/SPEC.md Cross-Cutting Concerns.
//
// Keys here are the single source of truth for agent colors -- AgentBubble
// (chat-ui) and AgentRosterStrip both read the same `--agent-{id}` custom
// properties injected at the dashboard layout root, so they render
// identical colors by construction.
export const mcatTheme: ThemeVars = {
  '--agent-aria': '#38bdf8',
  '--agent-mira': '#f472b6',
  '--agent-quinn': '#facc15',
  '--brand-primary': '#ffffff'
};
