import type { BaseAgent } from '../agent/base-agent';
import type { DomainConfig } from './domain-config';

export type DomainLookupResult = { found: true; config: DomainConfig } | { found: false };

export class UnresolvedAgentError extends Error {
  constructor(
    public readonly domainId: string,
    public readonly agentId: string,
  ) {
    super(`No registered constructor for agent "${agentId}" in domain "${domainId}"`);
    this.name = 'UnresolvedAgentError';
  }
}

/**
 * Self-registration pattern (decided, SPEC.md FR3): each domain package calls
 * register() as a side effect of import. No static domain list lives in core
 * or NEXUS — that's the only way adding a domain needs zero platform changes.
 */
export interface DomainRegistry {
  register(config: DomainConfig): void;
  resolveDomain(domainId: string): DomainLookupResult;
  resolveAgent(domainId: string, agentId: string): BaseAgent;
}

export function createDomainRegistry(): DomainRegistry {
  const domains = new Map<string, DomainConfig>();

  return {
    register(config) {
      domains.set(config.id, config);
    },

    resolveDomain(domainId) {
      const config = domains.get(domainId);
      return config ? { found: true, config } : { found: false };
    },

    resolveAgent(domainId, agentId) {
      const agentDef = domains.get(domainId)?.agents.find((a) => a.id === agentId);
      if (!agentDef) {
        throw new UnresolvedAgentError(domainId, agentId);
      }
      return agentDef.createAgent();
    },
  };
}
