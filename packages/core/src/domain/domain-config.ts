import type { BaseAgent } from '../agent/base-agent';

export interface AgentDef {
  id: string;
  displayName: string;
  createAgent: () => BaseAgent;
  config?: Record<string, unknown>;
}

export interface EvalCriterion {
  name: string;
  weight: number;
  description: string;
}

export interface EvalRubric {
  criteria: EvalCriterion[];
}

/**
 * CSS custom-property name/value pairs only (CLAUDE.md: "theme: ThemeVars //
 * CSS custom properties only") — no component overrides or non-CSS hooks.
 */
export type ThemeVars = {
  [key: `--${string}`]: string;
};

export interface Rule {
  condition: string;
  threshold?: number;
  action: 'escalate_to_human' | 'flag_for_review' | 'notify_instructor';
}

/**
 * The ONLY place domain-specific values live (CLAUDE.md architecture rule).
 * NEXUS, packages/ui, and apps/* must never branch on domain identity —
 * everything domain-specific flows through this schema.
 */
export interface DomainConfig {
  id: string;
  name: string;
  subdomain: string;
  agents: AgentDef[];
  contentIndex: string;
  evalRubric: EvalRubric;
  theme: ThemeVars;
  escalationRules: Rule[];
}
