# BaseAgent

## Definition

`BaseAgent` is the immutable abstract class every platform and domain agent extends (`packages/core/src/agent/base-agent.ts`). Per `CLAUDE.md`'s architecture rules, this contract is immutable — changing its shape is a breaking change across every domain and requires an ADR.

## Method Surface

| Method | Kind | Purpose |
|--------|------|---------|
| `fetchPrompt(): Promise<string>` | abstract | Fetch this agent's versioned system prompt from PromptRegistry (Langfuse). Never hardcoded, per `CLAUDE.md`. |
| `respond(input: AgentInput): AsyncIterable<AgentOutput>` | abstract | Subclass-specific agent logic. Produces a streamed sequence of `AgentOutput` chunks for a given turn. |
| `writeEpisodicMemory(input: AgentInput, output: AgentOutput): Promise<void>` | abstract | Persist this turn's output to episodic memory (Mem0 + pgvector). |
| `stream(input: AgentInput): AsyncIterable<AgentOutput>` | concrete | Orchestrates one full turn: `fetchPrompt()` → `respond()` (yielding each chunk) → `writeEpisodicMemory()` with the final chunk. This is what NEXUS / the SSE layer calls — never `respond()` directly. |

`readonly id: string` identifies which agent produced a given `AgentOutput`, for routing, handoff, and audit.

## Relationship to Other Contracts

- Consumes [`AgentInput`](./domain-config.md) and produces [`AgentOutput`](./domain-config.md) (see glossary for field lists).
- Referenced by [`AgentDef.createAgent()`](./domain-config.md) in `DomainConfig.agents` — NEXUS resolves an `AgentDef` to a `BaseAgent` instance via [`DomainRegistry`](./domain-registry.md).
- Domain agents (`domains/mcat/agents/*.ts`, and later `domains/gre`, `domains/dat`) extend `BaseAgent` directly. No domain-specific fields or methods may appear on `BaseAgent` itself.

## Constraints

- Must not import from any `domains/*` package.
- No domain-specific fields or methods (e.g. nothing named after MCAT/GRE/DAT concepts).
