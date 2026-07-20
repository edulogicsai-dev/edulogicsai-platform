import AgentRosterStrip from '@/components/ui/Dashboard/AgentRosterStrip';
import ChatContainer from '@/components/ui/Chat/ChatContainer';

// FR4: auth/profile gating and theme injection live in dashboard/layout.tsx
// (a redirect() thrown there aborts this page's render too) -- this page
// only mounts the chat surface.
export default function Dashboard() {
  return (
    <div className="flex flex-col h-full">
      <AgentRosterStrip />
      <ChatContainer />
    </div>
  );
}
