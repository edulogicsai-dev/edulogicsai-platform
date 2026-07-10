import type { AgentInput } from './agent-input';
import type { AgentOutput } from './agent-output';

/**
 * IMMUTABLE CONTRACT (CLAUDE.md: "BaseAgent contract is immutable").
 * Every domain agent extends this class (per specs/domain/glossary.md's
 * pre-existing entry — source of truth, not a fresh design). Changing its
 * shape is a breaking change across every domain — do not modify without an
 * ADR.
 */
export abstract class BaseAgent {
  abstract readonly id: string;

  /** Fetch this agent's versioned system prompt from PromptRegistry (Langfuse). Never hardcoded. */
  abstract fetchPrompt(): Promise<string>;

  /** Produce a streamed sequence of AgentOutput chunks for the given input. */
  abstract respond(input: AgentInput): AsyncIterable<AgentOutput>;

  /** Persist this turn's output to episodic memory (Mem0 + pgvector). */
  abstract writeEpisodicMemory(input: AgentInput, output: AgentOutput): Promise<void>;

  /**
   * Orchestrates one full turn: fetch this agent's prompt, stream the
   * response (SSE — never blocking JSON, per CLAUDE.md), then persist to
   * episodic memory. NEXUS/the SSE layer calls this, not respond() directly.
   */
  async *stream(input: AgentInput): AsyncIterable<AgentOutput> {
    await this.fetchPrompt();
    let last: AgentOutput | undefined;
    for await (const chunk of this.respond(input)) {
      last = chunk;
      yield chunk;
    }
    if (last) {
      await this.writeEpisodicMemory(input, last);
    }
  }
}
