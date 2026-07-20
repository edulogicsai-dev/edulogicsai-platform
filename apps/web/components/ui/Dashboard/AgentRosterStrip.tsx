import { agentRegistry } from '@/lib/agent-registry';

// Presentational only (FR3) -- pills have no click behavior. NEXUS decides
// handoffs server-side per CLAUDE.md's architecture rules, not the client.
// Colors come from the same `--agent-{id}` CSS vars AgentBubble (chat-ui)
// reads, injected once at the dashboard layout root (mcatTheme.ts) -- not
// duplicated here.
export default function AgentRosterStrip() {
  return (
    <div className="flex flex-wrap gap-2 px-4 py-2 border-b border-zinc-800">
      {Object.entries(agentRegistry).map(([agentId, meta]) => (
        <span
          key={agentId}
          className="flex items-center gap-1 px-3 py-1 text-sm rounded-full border"
          style={{ borderColor: `var(--agent-${agentId}, #71717a)` }}
        >
          <span aria-hidden="true">{meta.emoji}</span>
          <span className="text-zinc-200">{meta.name}</span>
        </span>
      ))}
    </div>
  );
}
