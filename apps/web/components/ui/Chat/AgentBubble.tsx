import { getAgentMeta } from '@/lib/agent-registry';
import type { ChatMessage } from '@/hooks/useAgentStream';

type AgentMessage = Extract<ChatMessage, { role: 'agent' }>;

export default function AgentBubble({ message }: { message: AgentMessage }) {
  const meta = getAgentMeta(message.agent_id);

  return (
    <div
      className="max-w-xl px-4 py-3 my-2 mr-auto rounded-md bg-zinc-800 border-l-4"
      style={{ borderColor: `var(--agent-${message.agent_id}, #71717a)` }}
    >
      <div className="flex items-center gap-2 mb-1 text-sm font-semibold text-zinc-300">
        <span aria-hidden="true">{meta.emoji}</span>
        <span>{meta.name}</span>
      </div>
      <p className="text-zinc-100 whitespace-pre-wrap">{message.response}</p>
    </div>
  );
}
