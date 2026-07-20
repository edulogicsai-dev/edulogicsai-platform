import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ChatContainer from './ChatContainer';
import type { ChatMessage } from '@/hooks/useAgentStream';

const send = vi.fn();
let mockState: {
  messages: ChatMessage[];
  streaming: boolean;
  activeAgentId: string | null;
};

vi.mock('@/hooks/useAgentStream', () => ({
  useAgentStream: () => ({ ...mockState, send })
}));

const agentMessage = (agentId: string, response: string): ChatMessage => ({
  role: 'agent',
  timestamp: '2026-07-20T00:00:00.000Z',
  agent_id: agentId,
  response,
  cited_chunks: [],
  suggested_handoff: null,
  mastery_update: null,
  session_notes: '',
  risk_level: 'low'
});

beforeEach(() => {
  send.mockClear();
  mockState = { messages: [], streaming: false, activeAgentId: null };
});

describe('ChatContainer', () => {
  it('AC1: renders a handoff cascade as 2 distinctly labeled bubbles in order', () => {
    mockState.messages = [agentMessage('aria', 'first reply'), agentMessage('mira', 'second reply')];

    render(<ChatContainer />);

    const names = screen.getAllByText(/^(ARIA|MIRA)$/);
    expect(names.map((n) => n.textContent)).toEqual(['ARIA', 'MIRA']);
    expect(screen.getByText('first reply')).toBeInTheDocument();
    expect(screen.getByText('second reply')).toBeInTheDocument();
  });

  it('AC2: disables input/pills and shows the indicator while streaming', () => {
    mockState.streaming = true;

    render(<ChatContainer />);

    expect(screen.getByPlaceholderText(/ask aria/i)).toBeDisabled();
    expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
    screen.getAllByRole('button', { name: /explain a concept|practice question|update my plan/i }).forEach((btn) =>
      expect(btn).toBeDisabled()
    );
    expect(screen.getByRole('status', { name: /agent is responding/i })).toBeInTheDocument();
  });

  it('AC2 (inverse): enables input/pills and hides the indicator when not streaming', () => {
    mockState.streaming = false;

    render(<ChatContainer />);

    expect(screen.getByPlaceholderText(/ask aria/i)).not.toBeDisabled();
    expect(screen.queryByRole('status', { name: /agent is responding/i })).not.toBeInTheDocument();
  });

  it('AC3: renders an error entry distinctly from agent/user bubbles', () => {
    mockState.messages = [
      { role: 'error', content: 'connection dropped', timestamp: '2026-07-20T00:00:00.000Z' }
    ];

    render(<ChatContainer />);

    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('connection dropped');
  });

  it('AC4: clicking a quick-action pill sends its exact label', () => {
    render(<ChatContainer />);

    fireEvent.click(screen.getByRole('button', { name: 'Practice question' }));

    expect(send).toHaveBeenCalledWith('Practice question');
  });

  it('AC5: an unrecognized agent_id falls back to a generic avatar/name without crashing', () => {
    mockState.messages = [agentMessage('sage', 'a future agent')];

    expect(() => render(<ChatContainer />)).not.toThrow();
    expect(screen.getByText('sage')).toBeInTheDocument();
    expect(screen.getByText('a future agent')).toBeInTheDocument();
  });
});
