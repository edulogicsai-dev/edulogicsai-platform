import type { ChatMessage } from '@/hooks/useAgentStream';

type ErrorMessage = Extract<ChatMessage, { role: 'error' }>;

// Deliberately distinct from both AgentBubble and UserBubble (FR3) -- a
// student should never mistake a dropped connection for an agent reply.
export default function ErrorBanner({ message }: { message: ErrorMessage }) {
  return (
    <div
      role="alert"
      className="max-w-xl px-4 py-3 my-2 mx-auto rounded-md border border-red-500 bg-red-950 text-red-200"
    >
      {message.content}
    </div>
  );
}
