'use client';

import { useAgentStream } from '@/hooks/useAgentStream';
import AgentBubble from './AgentBubble';
import UserBubble from './UserBubble';
import ErrorBanner from './ErrorBanner';
import StreamingIndicator from './StreamingIndicator';
import QuickActionPills from './QuickActionPills';
import MessageInput from './MessageInput';

export default function ChatContainer() {
  const { messages, streaming, send } = useAgentStream();

  // FR5: hide the indicator the instant the most recent message is an
  // agent bubble -- it only represents the gap before the *next* event.
  const lastMessage = messages[messages.length - 1];
  const waitingForNextEvent = streaming && lastMessage?.role !== 'agent';

  return (
    <div className="flex flex-col h-full min-h-[60vh]">
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.map((message, index) => {
          if (message.role === 'user') {
            return <UserBubble key={index} message={message} />;
          }
          if (message.role === 'agent') {
            return <AgentBubble key={index} message={message} />;
          }
          return <ErrorBanner key={index} message={message} />;
        })}
        {waitingForNextEvent && <StreamingIndicator />}
      </div>
      <div className="px-4 py-3 border-t border-zinc-800">
        <QuickActionPills onSelect={send} disabled={streaming} />
        <MessageInput onSubmit={send} disabled={streaming} />
      </div>
    </div>
  );
}
