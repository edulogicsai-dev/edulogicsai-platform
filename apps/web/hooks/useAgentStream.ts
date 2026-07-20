'use client';

import { useCallback, useState } from 'react';
import type { AgentOutput } from '@mcatai/core';
import { createClient } from '@/utils/supabase/client';
import { getAccessToken, DOMAIN_ID } from '@/utils/supabase/profile';

export type ChatMessage =
  | { role: 'user'; content: string; timestamp: string }
  | ({ role: 'agent'; timestamp: string } & AgentOutput)
  | { role: 'error'; content: string; timestamp: string };

export interface UseAgentStreamResult {
  messages: ChatMessage[];
  streaming: boolean;
  activeAgentId: string | null;
  send: (message: string) => void;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL;

function statusErrorMessage(status: number): string {
  if (status === 401) return 'Your session has expired. Please sign in again.';
  if (status === 403) return "You don't have access to this workspace.";
  if (status === 422) return 'That message could not be sent.';
  return 'Something went wrong. Please try again.';
}

interface SseHandlers {
  onMessage: (output: AgentOutput) => void;
  onError: (message: string) => void;
}

// FR2: browser EventSource can't send a POST body or an Authorization
// header, both of which /api/chat requires -- the stream is read and
// framed manually instead. AC5 requires this to be correct even when a
// single SSE event is split across two `reader.read()` chunks, so the
// buffer persists across reads rather than being parsed chunk-by-chunk.
async function parseSseStream(
  body: ReadableStream<Uint8Array>,
  handlers: SseHandlers
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  for (;;) {
    const { done, value } = await reader.read();
    if (value) {
      buffer += decoder.decode(value, { stream: true });
    }

    let boundary = buffer.indexOf('\n\n');
    while (boundary !== -1) {
      processSseEvent(buffer.slice(0, boundary), handlers);
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf('\n\n');
    }

    if (done) return;
  }
}

function processSseEvent(rawEvent: string, handlers: SseHandlers): void {
  let eventType = 'message';
  let data = '';

  for (const line of rawEvent.split('\n')) {
    if (line.startsWith('event:')) {
      eventType = line.slice('event:'.length).trim();
    } else if (line.startsWith('data:')) {
      data += line.slice('data:'.length).trim();
    }
  }

  if (eventType === 'done' || data === '') return;

  if (eventType === 'error') {
    try {
      const parsed = JSON.parse(data) as { error: string };
      handlers.onError(parsed.error);
    } catch {
      handlers.onError('Something went wrong processing your message.');
    }
    return;
  }

  if (eventType === 'message') {
    try {
      handlers.onMessage(JSON.parse(data) as AgentOutput);
    } catch {
      handlers.onError('Received an unreadable response from the server.');
    }
  }
}

export function useAgentStream(): UseAgentStreamResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [activeAgentId, setActiveAgentId] = useState<string | null>(null);

  const appendError = useCallback((content: string) => {
    setMessages((prev) => [
      ...prev,
      { role: 'error', content, timestamp: new Date().toISOString() }
    ]);
  }, []);

  const send = useCallback(
    (message: string) => {
      void (async () => {
        setMessages((prev) => [
          ...prev,
          { role: 'user', content: message, timestamp: new Date().toISOString() }
        ]);
        setStreaming(true);

        const supabase = createClient();
        const token = await getAccessToken(supabase);

        let response: Response;
        try {
          response = await fetch(`${API_URL}/api/chat`, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              message,
              // TODO(session_id-echo): sse-endpoint doesn't echo the
              // session_id it resolves server-side, and a client-generated
              // ID isn't safe to reuse (see SPEC.md Technical Design) --
              // always null until that's fixed. See
              // changes/2026/07/20/web-chat-integration/changes/sse-chat-hook/SPEC.md
              // Open Questions.
              session_id: null,
              tenant_id: DOMAIN_ID
            })
          });
        } catch {
          appendError(
            'Could not reach the server. Check your connection and try again.'
          );
          setStreaming(false);
          return;
        }

        if (!response.ok || !response.body) {
          appendError(statusErrorMessage(response.status));
          setStreaming(false);
          return;
        }

        await parseSseStream(response.body, {
          onMessage: (output) => {
            setActiveAgentId(output.agent_id);
            setMessages((prev) => [
              ...prev,
              { role: 'agent', timestamp: new Date().toISOString(), ...output }
            ]);
          },
          onError: appendError
        });

        setStreaming(false);
      })();
    },
    [appendError]
  );

  return { messages, streaming, activeAgentId, send };
}
