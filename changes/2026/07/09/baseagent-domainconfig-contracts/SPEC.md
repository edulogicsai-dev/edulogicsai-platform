---
title: BaseAgent Contract and DomainConfig Schema
type: feature
status: active
domain: platform
issue: TBD
created: 2026-07-09
updated: 2026-07-10
sdd_version: 7.3.0
affected_components:
  - core
---

## Overview

Define the immutable `BaseAgent` contract (`AgentInput`/`AgentOutput`) and the `DomainConfig` schema in `packages/core`. These are the two foundational TypeScript interfaces that every other part of the platform is built against: NEXUS loads a domain's agent roster from `DomainConfig`, every agent subclass (in `domains/mcat`, and later `domains/gre`, `domains/dat`) implements `BaseAgent`, and no other package is allowed to define competing shapes for either.

### Background

> Why is this change needed? What problem does it solve?

EduLogicsAI is a generic, domain-agnostic AI tutoring platform. MCATai is the reference implementation; GREai and DATai must be addable by writing a new `DomainConfig` and a set of domain agents — with **zero platform code changes**. That guarantee only holds if:

1. `BaseAgent` (`AgentInput`/`AgentOutput`) is defined once, is immutable, and every agent (platform or domain) is written against it.
2. `DomainConfig` is the single, complete schema describing a domain — its agents, content index, eval rubric, theme, and escalation rules — so NEXUS and shared UI never need domain-specific branches.

Without these contracts landing first, the planned database schema (multi-tenant tables, agent sessions, concept mastery, episodic memory, domain content store, prompt registry — see the paused `core-data-schema` epic) has no stable types to reference for agent I/O shape or domain identity, and downstream work would guess at shapes that later change.

### Current State

> What exists today? What are the limitations?

`packages/core/` exists as an empty/scaffolded package (per the monorepo structure in `CLAUDE.md`) with no `BaseAgent` or `DomainConfig` types defined yet. `domains/mcat/` has not yet been implemented against any contract. There is currently no compile-time guarantee that NEXUS or any agent implementation avoids domain-specific logic.

---

## User Stories

- As a platform engineer, I want a single `BaseAgent` interface so that every agent (NEXUS-orchestrated or domain-specific) can be invoked, streamed, and evaluated identically regardless of which domain it belongs to.
- As a domain engineer (e.g. building GREai), I want a complete `DomainConfig` schema so that I can register a new domain by writing config + agents, without touching `packages/core` or NEXUS.
- As NEXUS, I want to load an `AgentDef[]` roster from `DomainConfig` at boot so that I contain zero domain-specific logic.
- As the EVAL agent, I want `AgentOutput` to carry everything needed (content, streaming deltas, citations/usage metadata) so that Ragas/LLM-as-judge scoring doesn't need domain-specific adapters.

## Functional Requirements

### FR1: BaseAgent Contract

**Description:** Define the `BaseAgent` abstract contract and its `AgentInput`/`AgentOutput` types in `packages/core`.

**Behavior:**
- `BaseAgent` shall be an abstract class every domain agent extends, matching the pre-existing entry in `specs/domain/glossary.md` (discovered during implementation — see Gaps & Assumptions): abstract `fetchPrompt(): Promise<string>`, abstract `respond(input: AgentInput): AsyncIterable<AgentOutput>`, abstract `writeEpisodicMemory(input: AgentInput, output: AgentOutput): Promise<void>`, and a concrete `stream(input: AgentInput): AsyncIterable<AgentOutput>` that orchestrates the other three (fetch prompt → stream `respond()`'s chunks → persist via `writeEpisodicMemory()` on completion). `stream()`, not `respond()`, is what NEXUS/the SSE layer calls — this is what makes agent responses always streamed via SSE, never blocking JSON, per `CLAUDE.md`.
- `AgentInput` shall be explicit about its fields — all platform-level memory tiers, not domain-specific. Field names/casing match `specs/domain/glossary.md`'s pre-existing entry (source of truth):

  | Field | Type | Purpose |
  |-------|------|---------|
  | `tenant_id` | `string` | Tenant scoping for every downstream DB call |
  | `student_id` | `string` | Learner scoping for every downstream DB call |
  | `session_id` | `string` | Correlates the request to an agent session |
  | `message` | `string` | The current turn's user message/task payload |
  | `student_profile` | `StudentProfile` | Learner-level profile data (platform-level memory tier) |
  | `session_history` | `Message[]` | Working memory — prior conversational turns in the session |
  | `retrieved_chunks` | `ContentChunk[]` | RAG-retrieved content from the domain content store (pgvector) |
  | `episodic_context` | `EpisodicMemory[]` | Longer-horizon episodic memory (Mem0) relevant to this turn |

  `StudentProfile`, `Message`, `ContentChunk`, `EpisodicMemory`, and `MasteryDelta` (see `AgentOutput` below) are themselves platform-level types owned by `packages/core` (or re-exported from `packages/memory` where the tier is implemented) — they describe memory-tier shape, not domain content, so they do not violate the "no domain-specific fields" constraint below.
- `AgentOutput` shall be explicit about its fields — required for handoffs, governance, and the EVAL pipeline:

  | Field | Type | Purpose |
  |-------|------|---------|
  | `response` | `string` | The agent's (streamed, assembled) textual response |
  | `agent_id` | `string` | Which agent produced this output (for routing/handoff/audit) |
  | `cited_chunks` | `string[]` | IDs of `ContentChunk`s cited in `response`, for grounding/citation checks |
  | `suggested_handoff` | `string \| null` | Agent id to hand off to next, or `null` if none |
  | `mastery_update` | `MasteryDelta \| null` | FSRS-relevant concept mastery delta produced by this turn, or `null` |
  | `session_notes` | `string` | Free-text notes appended to session/episodic memory |
  | `risk_level` | `'low' \| 'medium' \| 'high'` | Escalation/governance signal consumed by `DomainConfig.escalationRules` |

  This shape is sufficient for `packages/eval`'s Ragas pipeline to score grounding (`cited_chunks`), and for NEXUS to act on handoffs (`suggested_handoff`) and HITL escalation (`risk_level`) without a domain-specific adapter.
- `BaseAgent` shall be declared in a way that marks it as an intentionally stable/immutable contract (e.g. a dedicated file with a clear "do not modify without an ADR" convention) per the `CLAUDE.md` rule "BaseAgent contract (AgentInput/AgentOutput) is immutable."

**Constraints:**
- No domain-specific fields (e.g. nothing named after MCAT/GRE/DAT concepts) may appear on `BaseAgent`, `AgentInput`, or `AgentOutput`.
- `BaseAgent` must not import from any `domains/*` package (enforced by package boundaries / lint rule, not just convention).

### FR2: DomainConfig Schema

**Description:** Define the `DomainConfig` interface (and its nested types: `AgentDef`, `EvalRubric`, `ThemeVars`, `Rule`) in `packages/core`, matching the schema already documented in `CLAUDE.md`.

**Behavior:**
- `DomainConfig` shall include: `id`, `name`, `subdomain`, `agents: AgentDef[]`, `contentIndex`, `evalRubric: EvalRubric`, `theme: ThemeVars`, `escalationRules: Rule[]`.
- `AgentDef` shall describe enough for NEXUS to load and route to an agent at boot (agent id/key, the `BaseAgent` implementation it maps to, and any per-agent config it needs) without NEXUS importing the domain package directly (e.g. via a registry lookup keyed by `id`).
- `ThemeVars` shall be restricted to CSS custom property name/value pairs only (per `CLAUDE.md`: "theme: ThemeVars // CSS custom properties only") — no component overrides or non-CSS styling hooks.
- `EvalRubric` shall express domain-specific scoring weights in a shape `packages/eval`'s Ragas pipeline can consume generically (weighted criteria, not domain-specific branching).
- `Rule` (escalation rules) shall express HITL (human-in-the-loop) escalation thresholds generically (condition + threshold + action), not as domain-specific if/else logic.

**Constraints:**
- `DomainConfig` must be the *only* place domain-specific values live — no domain conditionals may appear in `packages/core`, `packages/ui`, or `apps/*`.
- Adding a new domain must require zero changes to any file outside `domains/<new-domain>/`.

### FR3: DomainRegistry Loading Contract

**Description:** Define the minimal `DomainRegistry` interface in `packages/core` that NEXUS uses to look up a `DomainConfig` and resolve `AgentDef` entries to `BaseAgent` instances at boot, without domain-specific imports.

**Behavior:**
- Given a domain id (e.g. `'mcat'`), the registry shall return the matching `DomainConfig`.
- Given an `AgentDef`, the registry shall resolve to a constructed `BaseAgent` instance via a registration mechanism (each domain package registers its agent constructors), not via a hardcoded switch statement in core.
- Registration shall use the **self-registration pattern**: each domain package (`domains/mcat`, `domains/gre`, `domains/dat`) calls `DomainRegistry.register(domainConfig)` as a side effect of being imported (e.g. at the top of its entrypoint module), rather than NEXUS or `packages/core` importing a static list of domains.

**Constraints:**
- `packages/core`'s `DomainRegistry` implementation must not statically import any `domains/*` package.
- **Decided:** Self-registration is the only pattern that satisfies "adding a new domain requires zero changes outside `domains/<new-domain>/`" — a centrally configured list (e.g. NEXUS importing a static array of domains) would require editing a core/NEXUS file for every new domain, violating that guarantee. `packages/core` therefore exposes `register()` on `DomainRegistry` as public API; it does not expose or require a static domain list anywhere in core or NEXUS.

## Non-Functional Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| Type-only contract, zero runtime dependencies added | 0 new runtime deps in `packages/core` for these types | `package.json` diff review |
| Contract stability | Breaking changes require an explicit version bump / ADR note | Code review checklist |
| Build correctness | `packages/core` type-checks with no `any` in these types | `tsc --noEmit` in CI |

## Technical Design

### Architecture

```
domains/mcat/agents/*.ts  ─┐
domains/gre/agents/*.ts    ├─ implement ──> BaseAgent (packages/core)
domains/dat/agents/*.ts   ─┘

domains/{domain}/domain.config.ts ──> implements DomainConfig (packages/core)
                                              │
                                              ▼
                                    DomainRegistry (packages/core)
                                              │
                                              ▼
                                        NEXUS (apps/backend)
                                   (zero domain-specific logic)
```

### Data Model

> No database schema changes in this feature — this is a TypeScript types/contracts package. Table shapes that reference agent sessions / domain ids (in the paused `core-data-schema` epic) will be written against the types defined here.

**Modified Tables:** None (no DB changes in this feature).

### Algorithms / Business Logic

**DomainConfig resolution (conceptual):**

1. At NEXUS boot, iterate registered domains (each domain package self-registers its `DomainConfig` + agent constructors against `DomainRegistry`).
2. For an incoming request scoped to `tenantId`/domain, resolve `DomainConfig` by domain id.
3. For each `AgentDef` in `DomainConfig.agents`, resolve the constructor from the registry and instantiate a `BaseAgent`.
4. Route `AgentInput` to the resolved agent; stream `AgentOutput` back via SSE.

**Edge Cases:**
- Unknown domain id at lookup time: registry lookup shall return a typed "not found" result (not throw an untyped error) so callers can decide how to surface it.
- `AgentDef` referencing an agent id with no registered constructor: resolution shall fail with a typed error identifying the missing agent id and domain.

## API Contract

> N/A — this feature defines TypeScript types/interfaces in `packages/core`, not an HTTP API surface. No new endpoints are introduced.

## Security Considerations

- **Authentication:** N/A directly, but `AgentInput` must carry `tenantId`/`userId` so every downstream DB call built against it can be scoped per `CLAUDE.md`'s rule: "tenant_id + user_id MUST scope every DB query."
- **Authorization:** `DomainConfig.escalationRules` (HITL thresholds) is the generic mechanism by which domains express when an interaction must be escalated to a human — no domain-specific authorization logic belongs in `packages/core`.
- **Data Protection:** No secrets or `service_role` keys are part of these types; contracts are pure data shapes.
- **Input Validation:** `AgentInput`/`DomainConfig` shapes should be validated at the boundary (e.g. via a schema validator) where they're constructed from external input (API request, config file) — not inside `BaseAgent` implementations themselves.

## Error Handling

| Error Scenario | User Message | Log Level | Recovery |
|----------------|--------------|-----------|----------|
| Unknown domain id passed to `DomainRegistry` | N/A (internal/typed error) | ERROR | Caller (NEXUS) surfaces a 404-equivalent to the client |
| `AgentDef` with unresolvable agent constructor | N/A (internal/typed error) | ERROR | Fail domain registration at boot, not per-request |

## Observability

### Logging

| Event | Level | Fields |
|-------|-------|--------|
| Domain registered | INFO | domainId, agentCount |
| Agent resolution failed | ERROR | domainId, agentId |

### Metrics

| Metric | Type | Labels |
|--------|------|--------|
| domain_registered_total | counter | domainId |

### Traces

> N/A — no request-scoped tracing introduced by types alone; tracing spans belong to the agents/NEXUS implementation that will consume these contracts.

## Acceptance Criteria

- [ ] **AC1:** Given `packages/core` exports `BaseAgent`, `AgentInput`, and `AgentOutput`, when another package imports them, then no domain-specific field names appear anywhere in the three types.
- [ ] **AC2:** Given `packages/core` exports `DomainConfig` matching the `CLAUDE.md` schema (`id`, `name`, `subdomain`, `agents`, `contentIndex`, `evalRubric`, `theme`, `escalationRules`), when a domain author writes a `DomainConfig` object, then TypeScript rejects it if any required field is missing.
- [ ] **AC3:** Given a `DomainRegistry` implementation in `packages/core`, when it is statically analyzed for imports, then it contains zero imports from any `domains/*` path.
- [ ] **AC4:** Given `ThemeVars`, when a domain author attempts to add a non-CSS-custom-property field (e.g. a component override), then TypeScript rejects it.
- [ ] **AC5:** Given `AgentOutput`, when `packages/eval`'s Ragas pipeline consumes it, then it can extract content, usage, and citations without a domain-specific adapter.
- [ ] **AC6:** Given the full type surface, when `tsc --noEmit` runs on `packages/core`, then it passes with no `any` in `BaseAgent`, `AgentInput`, `AgentOutput`, or `DomainConfig`.

## Domain Model

> Comprehensive domain knowledge extracted from this change.

### Entities

| Entity | Definition | Spec Path | Status |
|--------|------------|-----------|--------|
| BaseAgent | The immutable contract every agent (platform or domain) implements to accept `AgentInput` and stream `AgentOutput` | specs/domain/definitions/base-agent.md | New |
| DomainConfig | The single schema describing a domain: its agents, content index, eval rubric, theme, and escalation rules | specs/domain/definitions/domain-config.md | New |
| AgentDef | A roster entry in `DomainConfig.agents` describing one agent NEXUS can load and route to | specs/domain/definitions/domain-config.md | New |
| DomainRegistry | The lookup mechanism NEXUS uses to resolve a domain id to its `DomainConfig` and agent constructors | specs/domain/definitions/domain-registry.md | New |

### Relationships

```text
DomainConfig ──has-many──► AgentDef
     │
     │ resolved-via
     ▼
DomainRegistry ──resolves──► BaseAgent (instance)
     ▲
     │ implements
Domain Agent (domains/mcat/agents/*.ts, etc.)
```

### Glossary

| Term | Definition | First Defined In |
|------|------------|-------------------|
| BaseAgent | The immutable base contract (`AgentInput`/`AgentOutput`) every agent implements | This spec |
| DomainConfig | The complete, domain-specific configuration schema consumed by NEXUS and shared UI | This spec |
| AgentDef | One entry in a `DomainConfig`'s agent roster | This spec |
| DomainRegistry | Core-owned lookup from domain id → `DomainConfig` and agent id → `BaseAgent` constructor | This spec |
| NEXUS | The domain-agnostic orchestrator that routes requests to agents via `DomainRegistry`; contains zero domain-specific logic | CLAUDE.md (existing) |

### Bounded Contexts

- **Core Contracts Context**: BaseAgent, AgentInput, AgentOutput, DomainConfig, AgentDef, DomainRegistry (this change)
- **Domain Context** (future): domains/mcat, domains/gre, domains/dat — each implements against this context's contracts

## Specs Directory Changes

### Before

```text
specs/
├── architecture/
│   └── overview.md
└── domain/
    └── glossary.md
```

### After

```text
specs/
├── architecture/
│   └── overview.md          # MODIFIED - add core contracts section (BaseAgent/DomainConfig flow)
└── domain/
    ├── glossary.md           # MODIFIED - add BaseAgent, DomainConfig, AgentDef, DomainRegistry terms
    └── definitions/
        ├── base-agent.md     # NEW
        ├── domain-config.md  # NEW
        └── domain-registry.md # NEW
```

### Changes Summary

| Path | Action | Description |
|------|--------|-------------|
| specs/domain/glossary.md | Modify | Add BaseAgent, DomainConfig, AgentDef, DomainRegistry terms |
| specs/domain/definitions/base-agent.md | Create | Full definition of the BaseAgent contract and its immutability rule |
| specs/domain/definitions/domain-config.md | Create | Full definition of DomainConfig and AgentDef schemas |
| specs/domain/definitions/domain-registry.md | Create | Full definition of the DomainRegistry lookup contract |
| specs/architecture/overview.md | Modify | Add a section showing how domains register against core via DomainConfig/DomainRegistry |

## Components

> `packages/core` is not yet a registered SDD component (no component type in the active `fullstack-typescript` tech pack cleanly models a shared TypeScript library package — see Open Questions). This section documents the change without relying on tech-pack component scaffolding.

### New Components

| Component | Type | Settings | Purpose |
|-----------|------|----------|---------|
| N/A | N/A | N/A | Not scaffolded via tech-pack component types in this change (see Open Questions) |

### Modified Components

| Component | Changes |
|-----------|---------|
| packages/core (existing monorepo package, untracked as an SDD component) | Add `BaseAgent`, `AgentInput`, `AgentOutput`, `DomainConfig`, `AgentDef`, `EvalRubric`, `ThemeVars`, `Rule`, `DomainRegistry` |

## System Analysis

### Inferred Requirements

- `packages/eval`'s `EvalRubric` consumption and `packages/memory`'s FSRS/episodic types will need to reference these contracts once they land — out of scope here, but this spec's types should anticipate that consumption (e.g. `AgentOutput` metadata shape).

### Gaps & Assumptions

- Assumes `packages/core` already exists as an empty/scaffolded package per the monorepo layout in `CLAUDE.md` (not yet verified by directory listing at spec time).
- Discovered during implementation: `specs/domain/glossary.md` and `specs/architecture/overview.md` already contained `BaseAgent`/`AgentInput`/`AgentOutput`/`DomainConfig` entries from an earlier commit, predating this change, with a different shape than originally drafted here (abstract class with `fetchPrompt`/`respond`/`writeEpisodicMemory`/`stream` rather than a single `run()` method; snake_case `tenant_id`/`student_id`/`session_id` plus an explicit `message` field, rather than camelCase with no `message` field). Resolved in favor of the pre-existing glossary as source of truth — FR1 above reflects the as-built shape, not the original draft. `AgentOutput`'s shape was already consistent between both and required no change.
- No TypeScript tooling existed anywhere in the repo prior to this change (no tsconfig, no installed dependencies, no root config). Bootstrapped minimal infra as part of this change: root `tsconfig.base.json` (strict, matching apps/web and apps/mobile conventions), `typescript` + `vitest` as root devDependencies, and a per-package `tsconfig.json`/`vitest.config.ts` for `packages/core`.

### Cross-References

- Paused: `changes/.../core-data-schema` epic (multi-tenant DB schema) — depends on the types defined here for agent session / domain id shapes.
- `CLAUDE.md` — Architecture Rules, DomainConfig Schema section (source of truth this spec formalizes into code).

## Requirements Discovery

### Questions & Answers

| Step | Question | Answer |
|------|----------|--------|
| Context | What feature to build next, given the DB epic was paused? | BaseAgent contract and DomainConfig first, since the database schema depends on those types |
| Scope | Domain for this change? | Platform-wide / core |
| Scope | Tech-pack fit (Node/K8s tech pack vs. actual Python/FastAPI + Supabase + Vercel/Railway stack)? | Defer — this change is TypeScript-only (packages/core), revisit when touching Python backend or DB components |

### User Feedback

- User explicitly paused the `core-data-schema` epic mid-flow because it depends on these contracts existing first.
- Pre-approval revision requested: make `AgentInput`/`AgentOutput` fields explicit (see FR1) rather than describing them generically; resolve the `DomainRegistry` registration open question in favor of self-registration (see FR3), since it's the only pattern satisfying the zero-platform-change guarantee for new domains.

## Domain Updates

### Glossary Terms

| Term | Definition | Action |
|------|------------|--------|
| BaseAgent | The immutable abstract class every platform or domain agent extends | already existed (pre-dated this change); implementation conformed to it |
| AgentInput | Immutable contract fields (`tenant_id`, `student_id`, `session_id`, `message`, `student_profile`, `session_history`, `retrieved_chunks`, `episodic_context`) | already existed (pre-dated this change); implementation conformed to it |
| AgentOutput | Immutable contract fields (`response`, `agent_id`, `cited_chunks`, `suggested_handoff`, `mastery_update`, `session_notes`, `risk_level`) | already existed (pre-dated this change); matched as-drafted |
| DomainConfig | The complete schema describing a domain (agents, content index, eval rubric, theme, escalation rules); the only place domain-specific logic lives | already existed (pre-dated this change); matched as-drafted |
| AgentDef | One roster entry in `DomainConfig.agents` describing an agent NEXUS can load | add (new) |
| DomainRegistry | Core-owned lookup mechanism from domain id to `DomainConfig` and from agent id to `BaseAgent` instance | add (new) |

### Definition Specs

| File | Description | Action |
|------|-------------|--------|
| `base-agent.md` | Full definition of BaseAgent, AgentInput, AgentOutput and the immutability rule | create |
| `domain-config.md` | Full definition of DomainConfig, AgentDef, EvalRubric, ThemeVars, Rule | create |
| `domain-registry.md` | Full definition of the DomainRegistry lookup contract and boot-time registration flow | create |

### Architecture Docs

- [ ] Update `specs/architecture/overview.md` with a section on how domains register against `packages/core` via `DomainConfig` + `DomainRegistry`, and how NEXUS stays domain-agnostic.

## Testing Strategy

### Unit Tests

| Component | Test Case | Expected Behavior |
|-----------|-----------|-------------------|
| packages/core types | Construct a valid `DomainConfig` object literal | Type-checks with no errors |
| packages/core types | Construct a `DomainConfig` missing a required field | Fails to type-check (compile-time test, e.g. via `tsd` or `expectTypeOf`) |
| packages/core types | Add a non-CSS field to `ThemeVars` | Fails to type-check |
| DomainRegistry | Register a domain, resolve by id | Returns the registered `DomainConfig` |
| DomainRegistry | Resolve an unknown domain id | Returns typed "not found" result, does not throw |
| DomainRegistry | Resolve an `AgentDef` with no registered constructor | Returns/throws a typed error identifying domain + agent id |

### Integration Tests

| Scenario | Components | Expected Outcome |
|----------|------------|-------------------|
| N/A | N/A | This change has no runtime service integration; deferred to the change that implements NEXUS boot-time domain loading |

### E2E Tests

| User Flow | Steps | Expected Result |
|-----------|-------|------------------|
| N/A | N/A | No user-facing flow in this types-only change |

### Test Data

| Entity | Required State | Purpose |
|--------|-----------------|---------|
| Fixture `DomainConfig` (e.g. minimal fake domain) | Valid, minimal | Used across unit tests to exercise `DomainRegistry` without depending on a real domain package |

## Dependencies

### Internal Dependencies

| Component | Version | Reason |
|-----------|---------|--------|
| packages/core | N/A (this change creates the types) | Nothing yet depends on these types; they are net-new |

### External Dependencies

| Service | API Version | Fallback |
|---------|--------------|----------|
| N/A | N/A | No external services in this change |

## Migration / Rollback

### Migration Steps

1. Add the new type files to `packages/core`.
2. Export them from the package's public entrypoint.

### Rollback Plan

1. Since nothing yet depends on these types (they're net-new), rollback is simply reverting the commit/PR.

### Feature Flags

| Flag | Default | Purpose |
|------|---------|---------|
| N/A | N/A | Not applicable — internal types, no runtime behavior to flag |

## Out of Scope

- Implementing NEXUS's actual boot-time loading logic (registry wiring, HTTP server) — out of scope; only the `DomainRegistry` *interface* is defined here.
- Implementing any concrete `domains/mcat` agent against `BaseAgent` — out of scope; tracked as future work once this contract lands.
- The paused `core-data-schema` epic (multi-tenant DB schema, pgvector, FSRS, episodic memory, prompt registry) — explicitly deferred until these contracts exist.
- `packages/eval`'s Ragas pipeline implementation — out of scope; this spec only ensures `AgentOutput`'s shape is sufficient for it.

## Open Questions

- [ ] Does `packages/core` need to be registered as a first-class SDD component? The active `fullstack-typescript` tech pack's component types (`config`, `contract`, `database`, `server`, `webapp`, `helm`, `integration-testing`, `e2e-testing`, `cicd`) have no type for a shared TypeScript library package — this spec proceeds without one; may need a tech-pack or settings change if this recurs for `packages/ui`, `packages/memory`, `packages/eval`.

## References

- CLAUDE.md — Architecture Rules, DomainConfig Schema, Monorepo Structure sections
- Paused epic: `core-data-schema` (multi-tenant DB schema, pgvector, FSRS, episodic memory, prompt registry)
