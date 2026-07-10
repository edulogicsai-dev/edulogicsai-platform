# DomainConfig

## Definition

`DomainConfig` (`packages/core/src/domain/domain-config.ts`) is the single, complete schema describing a domain product (MCATai, GREai, DATai). Per `CLAUDE.md`'s architecture rules, it is the *only* place domain-specific values live — NEXUS, `packages/ui`, and `apps/*` never branch on domain identity.

## Schema

| Field | Type | Purpose |
|-------|------|---------|
| `id` | `string` | Domain identifier (e.g. `'mcat'`), used as the `DomainRegistry` lookup key |
| `name` | `string` | Display name (e.g. `'MCATai'`) |
| `subdomain` | `string` | Subdomain the domain is served from (e.g. `'app.mcatai.co'`) |
| `agents` | `AgentDef[]` | The agent roster NEXUS loads at boot |
| `contentIndex` | `string` | pgvector namespace holding this domain's content chunks |
| `evalRubric` | `EvalRubric` | Domain-specific scoring weights consumed generically by `packages/eval`'s Ragas pipeline |
| `theme` | `ThemeVars` | CSS custom property name/value pairs only — no component overrides |
| `escalationRules` | `Rule[]` | HITL escalation thresholds (condition + threshold + action) |

### AgentDef

| Field | Type | Purpose |
|-------|------|---------|
| `id` | `string` | Agent identifier, matched against `AgentOutput.suggested_handoff` and `DomainRegistry.resolveAgent` |
| `displayName` | `string` | Human-readable name |
| `createAgent` | `() => BaseAgent` | Factory NEXUS calls to instantiate this agent, without importing the domain package directly |
| `config` | `Record<string, unknown>` (optional) | Per-agent configuration |

### EvalRubric / EvalCriterion

`EvalRubric.criteria: EvalCriterion[]`, each with `name`, `weight` (0–1), and `description` — a generic weighted-criteria shape, not domain-specific branching logic.

### ThemeVars

`{ [key: \`--${string}\`]: string }` — CSS custom property names only (must start with `--`). TypeScript rejects any non-CSS-custom-property key on a `ThemeVars` object literal.

### Rule

Escalation rule: `condition: string`, `threshold?: number`, `action: 'escalate_to_human' | 'flag_for_review' | 'notify_instructor'` — generic HITL semantics, not domain-specific if/else logic.

## Constraints

- Adding a new domain requires zero changes to any file outside `domains/<new-domain>/`.
- All required fields are non-optional — omitting one fails to type-check.

## Related

- [`BaseAgent`](./base-agent.md) — what `AgentDef.createAgent()` instantiates.
- [`DomainRegistry`](./domain-registry.md) — resolves `DomainConfig` by domain id and `AgentDef` entries to `BaseAgent` instances.
