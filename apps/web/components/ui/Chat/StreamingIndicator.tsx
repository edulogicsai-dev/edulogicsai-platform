// Per-agent-hop indicator, not a per-token typewriter -- the backend
// streams one SSE event per agent in the handoff cascade, not per token
// (see epic Cross-Cutting Concerns). Rendered by ChatContainer only in the
// gap before the next event arrives.
export default function StreamingIndicator() {
  return (
    <div
      className="flex items-center gap-1 px-4 py-3 my-2 mr-auto"
      role="status"
      aria-live="polite"
      aria-label="Agent is responding"
    >
      <span className="w-2 h-2 rounded-full bg-zinc-400 animate-bounce [animation-delay:-0.3s]" />
      <span className="w-2 h-2 rounded-full bg-zinc-400 animate-bounce [animation-delay:-0.15s]" />
      <span className="w-2 h-2 rounded-full bg-zinc-400 animate-bounce" />
    </div>
  );
}
