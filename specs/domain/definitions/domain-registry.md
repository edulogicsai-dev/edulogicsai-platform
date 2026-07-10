# DomainRegistry

## Definition

`DomainRegistry` (`packages/core/src/domain/domain-registry.ts`) is the core-owned lookup mechanism NEXUS uses to resolve a domain id to its [`DomainConfig`](./domain-config.md), and an agent id within that domain to a constructed [`BaseAgent`](./base-agent.md) instance — without `packages/core` or NEXUS ever importing a `domains/*` package.

## Registration Pattern: Self-Registration (Decided)

Each domain package (`domains/mcat`, `domains/gre`, `domains/dat`) calls `DomainRegistry.register(domainConfig)` as a side effect of being imported (e.g. at the top of its entrypoint module). NEXUS does not import a static list of domains.

This is the only pattern that satisfies "adding a new domain requires zero changes outside `domains/<new-domain>/`" — a centrally configured list would require editing a core/NEXUS file for every new domain.

## API

| Method | Behavior |
|--------|----------|
| `register(config: DomainConfig): void` | Registers a domain's config, keyed by `config.id`. |
| `resolveDomain(domainId: string): DomainLookupResult` | Returns `{ found: true, config }` or `{ found: false }`. Never throws on an unknown domain id. |
| `resolveAgent(domainId: string, agentId: string): BaseAgent` | Looks up the domain's `AgentDef` by agent id and calls its `createAgent()` factory. Throws `UnresolvedAgentError` (identifying both `domainId` and `agentId`) if no matching `AgentDef` is registered. |

`createDomainRegistry()` returns a minimal in-memory implementation (`Map<string, DomainConfig>`).

## Constraints

- Zero imports from any `domains/*` path.
- Unknown-domain lookups return a typed "not found" result rather than throwing.
- Unresolvable agent lookups throw a typed `UnresolvedAgentError`, not a generic error.

## Related

- [`DomainConfig`](./domain-config.md) — what gets registered.
- [`BaseAgent`](./base-agent.md) — what `resolveAgent()` returns.
