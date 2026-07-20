import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import AgentRosterStrip from './AgentRosterStrip';
import AgentBubble from '@/components/ui/Chat/AgentBubble';
import type { ChatMessage } from '@/hooks/useAgentStream';

describe('AgentRosterStrip', () => {
  it('renders one pill per registered agent with name and emoji', () => {
    render(<AgentRosterStrip />);

    expect(screen.getByText('ARIA')).toBeInTheDocument();
    expect(screen.getByText('MIRA')).toBeInTheDocument();
    expect(screen.getByText('QUINN')).toBeInTheDocument();
  });

  it("AC5: uses the same --agent-{id} CSS var (and fallback) as chat-ui's AgentBubble for a given agent, not an independently hardcoded color", () => {
    render(<AgentRosterStrip />);
    const ariaPill = screen.getByText('ARIA').closest('span[style]') as HTMLElement | null;

    const ariaMessage: Extract<ChatMessage, { role: 'agent' }> = {
      role: 'agent',
      timestamp: '2026-07-20T00:00:00.000Z',
      agent_id: 'aria',
      response: 'hi',
      cited_chunks: [],
      suggested_handoff: null,
      mastery_update: null,
      session_notes: '',
      risk_level: 'low'
    };
    render(<AgentBubble message={ariaMessage} />);
    const bubble = screen.getByText('hi').closest('div[style]') as HTMLElement | null;

    expect(ariaPill?.style.borderColor).toBe(bubble?.style.borderColor);
    expect(ariaPill?.style.borderColor).toBe('var(--agent-aria, #71717a)');
  });
});
