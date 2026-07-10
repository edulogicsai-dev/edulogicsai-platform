import { describe, expect, it } from 'vitest';
import { BaseAgent } from '../agent/base-agent';
import type { AgentInput } from '../agent/agent-input';
import type { AgentOutput } from '../agent/agent-output';
import type { DomainConfig } from './domain-config';
import { UnresolvedAgentError, createDomainRegistry } from './domain-registry';

class FixtureAgent extends BaseAgent {
  constructor(public readonly id: string) {
    super();
  }

  async fetchPrompt(): Promise<string> {
    return 'fixture prompt';
  }

  async *respond(_input: AgentInput): AsyncIterable<AgentOutput> {
    yield {
      response: 'ok',
      agent_id: this.id,
      cited_chunks: [],
      suggested_handoff: null,
      mastery_update: null,
      session_notes: '',
      risk_level: 'low',
    };
  }

  async writeEpisodicMemory(_input: AgentInput, _output: AgentOutput): Promise<void> {}
}

function makeFixtureAgent(id: string): BaseAgent {
  return new FixtureAgent(id);
}

function makeFixtureDomainConfig(): DomainConfig {
  return {
    id: 'fake-domain',
    name: 'Fake Domain',
    subdomain: 'app.fake.co',
    agents: [{ id: 'tutor', displayName: 'Tutor', createAgent: () => makeFixtureAgent('tutor') }],
    contentIndex: 'fake_content',
    evalRubric: { criteria: [{ name: 'accuracy', weight: 1, description: 'Correctness' }] },
    theme: { '--color-primary': '#000000' },
    escalationRules: [{ condition: 'risk_level == "high"', action: 'escalate_to_human' }],
  };
}

describe('DomainRegistry', () => {
  it('registers a domain and resolves it by id', () => {
    const registry = createDomainRegistry();
    const config = makeFixtureDomainConfig();
    registry.register(config);

    const result = registry.resolveDomain('fake-domain');
    expect(result.found).toBe(true);
    if (result.found) {
      expect(result.config).toBe(config);
    }
  });

  it('returns a typed not-found result for an unknown domain id, without throwing', () => {
    const registry = createDomainRegistry();
    const result = registry.resolveDomain('unknown-domain');
    expect(result.found).toBe(false);
  });

  it('resolves a registered agent constructor', () => {
    const registry = createDomainRegistry();
    registry.register(makeFixtureDomainConfig());

    const agent = registry.resolveAgent('fake-domain', 'tutor');
    expect(agent.id).toBe('tutor');
  });

  it('throws a typed error identifying domain + agent id for a missing agent constructor', () => {
    const registry = createDomainRegistry();
    registry.register(makeFixtureDomainConfig());

    expect(() => registry.resolveAgent('fake-domain', 'missing-agent')).toThrow(UnresolvedAgentError);

    try {
      registry.resolveAgent('fake-domain', 'missing-agent');
      expect.unreachable();
    } catch (error) {
      expect(error).toBeInstanceOf(UnresolvedAgentError);
      const unresolved = error as UnresolvedAgentError;
      expect(unresolved.domainId).toBe('fake-domain');
      expect(unresolved.agentId).toBe('missing-agent');
    }
  });
});
