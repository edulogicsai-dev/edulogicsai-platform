import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { useAgentStream } from './useAgentStream';

vi.mock('@/utils/supabase/client', () => ({
  createClient: () => ({})
}));

vi.mock('@/utils/supabase/profile', () => ({
  getAccessToken: async () => 'test-token',
  DOMAIN_ID: 'mcat'
}));

const agentOutput = (agentId: string, response: string) => ({
  agent_id: agentId,
  response,
  cited_chunks: [],
  suggested_handoff: null,
  mastery_update: null,
  session_notes: '',
  risk_level: 'low'
});

function sseEvent(event: string, data: unknown): string {
  const payload = data === undefined ? '' : JSON.stringify(data);
  return `event: ${event}\ndata: ${payload}\n\n`;
}

// Enqueues one chunk per pull() call, yielding a macrotask (not just a
// microtask) in between so each SSE event is genuinely processed as its
// own React render step -- AC2 needs to observe the intermediate
// activeAgentId via testing-library's timer-based waitFor, not just race
// straight to the final value.
function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let i = 0;
  return new ReadableStream<Uint8Array>({
    async pull(controller) {
      if (i < chunks.length) {
        // Long enough to exceed waitFor's default 50ms poll interval, so
        // the intermediate 'aria' state is observably caught before 'mira'
        // arrives, rather than both landing between two polls.
        await new Promise((resolve) => setTimeout(resolve, 150));
        controller.enqueue(encoder.encode(chunks[i]));
        i++;
      } else {
        controller.close();
      }
    }
  });
}

interface MockFetchResponse {
  ok: boolean;
  status: number;
  body: ReadableStream<Uint8Array> | null;
}

function mockFetchOnce(response: MockFetchResponse) {
  return vi.fn().mockResolvedValue(response as unknown as Response);
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('useAgentStream', () => {
  it('AC1: single message + done yields 1 user + 1 agent message, streaming ends false', async () => {
    global.fetch = mockFetchOnce({
      ok: true,
      status: 200,
      body: streamOf([
        sseEvent('message', agentOutput('aria', 'hello')),
        sseEvent('done', undefined)
      ])
    });

    const { result } = renderHook(() => useAgentStream());

    act(() => {
      result.current.send('hi');
    });

    await waitFor(() => expect(result.current.streaming).toBe(false));

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0]).toMatchObject({ role: 'user', content: 'hi' });
    expect(result.current.messages[1]).toMatchObject({ role: 'agent', agent_id: 'aria' });
  });

  it('AC2: activeAgentId transitions aria -> mira across a handoff cascade', async () => {
    global.fetch = mockFetchOnce({
      ok: true,
      status: 200,
      body: streamOf([
        sseEvent('message', agentOutput('aria', 'frustration detected')),
        sseEvent('message', agentOutput('mira', 'taking over')),
        sseEvent('done', undefined)
      ])
    });

    const { result } = renderHook(() => useAgentStream());
    const observed: (string | null)[] = [];

    act(() => {
      result.current.send('hi');
    });

    await waitFor(() => expect(result.current.activeAgentId).toBe('aria'));
    observed.push(result.current.activeAgentId);

    await waitFor(() => expect(result.current.activeAgentId).toBe('mira'));
    observed.push(result.current.activeAgentId);

    await waitFor(() => expect(result.current.streaming).toBe(false));

    expect(observed).toEqual(['aria', 'mira']);
    const agentMessages = result.current.messages.filter((m) => m.role === 'agent');
    expect(agentMessages.map((m: any) => m.agent_id)).toEqual(['aria', 'mira']);
  });

  it('AC3: event: error produces a role: error entry and ends streaming', async () => {
    global.fetch = mockFetchOnce({
      ok: true,
      status: 200,
      body: streamOf([sseEvent('error', { error: 'turn failed' })])
    });

    const { result } = renderHook(() => useAgentStream());

    act(() => {
      result.current.send('hi');
    });

    await waitFor(() => expect(result.current.streaming).toBe(false));

    const errorEntry = result.current.messages.find((m) => m.role === 'error');
    expect(errorEntry).toMatchObject({ role: 'error', content: 'turn failed' });
  });

  it('AC4: HTTP 401 does not attempt SSE parsing and adds an error entry', async () => {
    global.fetch = mockFetchOnce({ ok: false, status: 401, body: null });

    const { result } = renderHook(() => useAgentStream());

    act(() => {
      result.current.send('hi');
    });

    await waitFor(() => expect(result.current.streaming).toBe(false));

    const errorEntry = result.current.messages.find((m) => m.role === 'error');
    expect(errorEntry).toBeDefined();
    expect((errorEntry as any).content).toMatch(/session has expired/i);
  });

  it('AC5: a single SSE event split across two chunks is still parsed correctly', async () => {
    const full = sseEvent('message', agentOutput('quinn', 'split across chunks'));
    const splitPoint = Math.floor(full.length / 2);

    global.fetch = mockFetchOnce({
      ok: true,
      status: 200,
      body: streamOf([full.slice(0, splitPoint), full.slice(splitPoint)])
    });

    const { result } = renderHook(() => useAgentStream());

    act(() => {
      result.current.send('hi');
    });

    await waitFor(() => expect(result.current.streaming).toBe(false));

    const agentMessages = result.current.messages.filter((m) => m.role === 'agent');
    expect(agentMessages).toHaveLength(1);
    expect(agentMessages[0]).toMatchObject({ agent_id: 'quinn', response: 'split across chunks' });
  });

  it('AC6: session_id is null on every call, not a reused client-generated ID', async () => {
    const fetchMock = vi.fn().mockImplementation(
      async () =>
        ({
          ok: true,
          status: 200,
          body: streamOf([sseEvent('done', undefined)])
        }) as unknown as Response
    );
    global.fetch = fetchMock;

    const { result } = renderHook(() => useAgentStream());

    act(() => {
      result.current.send('first');
    });
    await waitFor(() => expect(result.current.streaming).toBe(false));

    act(() => {
      result.current.send('second');
    });
    await waitFor(() => expect(result.current.streaming).toBe(false));

    expect(fetchMock).toHaveBeenCalledTimes(2);
    for (const call of fetchMock.mock.calls) {
      const body = JSON.parse(call[1].body as string);
      expect(body.session_id).toBeNull();
    }
  });
});
