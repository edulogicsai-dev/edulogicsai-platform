// Shared between chat-ui (bubbles) and dashboard-layout (agent roster strip)
// so both render identical names/avatars for the same agent_id by
// construction, not by keeping two hardcoded lists in sync manually. See
// changes/2026/07/20/web-chat-integration/SPEC.md Cross-Cutting Concerns:
// no backend agent-metadata endpoint exists yet, so this is a hardcoded
// stand-in for a future DomainConfig.agents-driven source.
export interface AgentMeta {
  name: string;
  emoji: string;
}

export const agentRegistry: Record<string, AgentMeta> = {
  aria: { name: 'ARIA', emoji: '🧭' },
  mira: { name: 'MIRA', emoji: '💙' },
  quinn: { name: 'QUINN', emoji: '📝' }
};

const DEFAULT_EMOJI = '🤖';

// An unrecognized agent_id (a future agent not yet added here) falls back
// to a generic avatar + the raw agent_id as the name, not a crash.
export function getAgentMeta(agentId: string): AgentMeta {
  return agentRegistry[agentId] ?? { name: agentId, emoji: DEFAULT_EMOJI };
}
