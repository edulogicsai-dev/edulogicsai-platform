import type { ChatMessage } from '@/hooks/useAgentStream';

type UserMessage = Extract<ChatMessage, { role: 'user' }>;

export default function UserBubble({ message }: { message: UserMessage }) {
  return (
    <div className="max-w-xl px-4 py-3 my-2 ml-auto rounded-md bg-white text-zinc-900">
      <p className="whitespace-pre-wrap">{message.content}</p>
    </div>
  );
}
