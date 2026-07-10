---
title: BaseAgent Contract and DomainConfig Schema - Implementation Plan
change: baseagent-domainconfig-contracts
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-09
sdd_version: 7.3.0
---

## Overview

Implementation plan for: BaseAgent Contract and DomainConfig Schema

Specification: [SPEC.md](./SPEC.md)

## Affected Components

<!-- packages/core is not a registered SDD component in sdd/sdd-settings.yaml — the active
     fullstack-typescript tech pack has no component type for a shared TypeScript library
     package (only config, contract, database, server, webapp, helm, integration-testing,
     e2e-testing, cicd). Phases below are hand-authored rather than generated from the
     tech pack's dependency graph / agent-assignment machinery. See SPEC.md Open Questions. -->
- packages/core (untracked as an SDD component)

## Prerequisites

None — this is the first change in the platform's contract layer. It is a prerequisite *for* the paused `core-data-schema` epic, not the other way around.

## Implementation Phases

### Phase 1: BaseAgent Contract

**Component:** packages/core
**Standards:** typescript-standards

Tasks:
- [x] Define `AgentInput` type: `tenant_id`, `student_id`, `session_id`, `message`, `student_profile: StudentProfile`, `session_history: Message[]`, `retrieved_chunks: ContentChunk[]`, `episodic_context: EpisodicMemory[]` — field names/casing conformed to the pre-existing `specs/domain/glossary.md` entry (discovered during implementation; source of truth over the original draft)
- [x] Define `AgentOutput` type: `response: string`, `agent_id: string`, `cited_chunks: string[]`, `suggested_handoff: string | null`, `mastery_update: MasteryDelta | null`, `session_notes: string`, `risk_level: 'low' | 'medium' | 'high'`
- [x] Define `StudentProfile`, `Message`, `ContentChunk`, `EpisodicMemory`, `MasteryDelta` as platform-level supporting types (owned by `packages/core`)
- [x] Define `BaseAgent` as an abstract class (conformed to pre-existing glossary entry, not the original single-`run()`-method draft): abstract `fetchPrompt()`, `respond()`, `writeEpisodicMemory()`; concrete `stream()` orchestrating the three
- [x] Add a clear "immutable contract, do not modify without an ADR" convention (file header or doc comment) per CLAUDE.md's rule
- [x] Ensure zero domain-specific imports or field names in these files (verified via grep audit)

Deliverables:
- `packages/core` exports `BaseAgent`, `AgentInput`, `AgentOutput`
- Type-only, zero new runtime dependencies

### Phase 2: DomainConfig Schema

**Component:** packages/core
**Standards:** typescript-standards

Tasks:
- [x] Define `AgentDef` (agent id, display name, `createAgent(): BaseAgent` factory, optional per-agent config)
- [x] Define `EvalRubric`/`EvalCriterion` (generic weighted-criteria shape consumable by `packages/eval`'s Ragas pipeline)
- [x] Define `ThemeVars` restricted to CSS custom property name/value pairs only, via a `` `--${string}` `` pattern index signature
- [x] Define `Rule` (escalation rule: condition + threshold + action) for HITL escalation
- [x] Define `DomainConfig` composing the above: `id`, `name`, `subdomain`, `agents: AgentDef[]`, `contentIndex`, `evalRubric`, `theme`, `escalationRules`
- [x] Verify required fields are non-optional so omitting one fails to type-check (AC2) — covered by compile-time `@ts-expect-error` test
- [x] Verify `ThemeVars` rejects non-CSS-custom-property fields (AC4) — covered by compile-time `@ts-expect-error` test

Deliverables:
- `packages/core` exports `DomainConfig`, `AgentDef`, `EvalRubric`, `ThemeVars`, `Rule`
- Schema matches CLAUDE.md's documented `DomainConfig` shape exactly

### Phase 3: DomainRegistry Lookup Contract

**Component:** packages/core
**Standards:** typescript-standards, unit-testing

Tasks:
- [x] Define `DomainRegistry` interface: domain id → `DomainConfig` lookup; agent id → `BaseAgent` constructor resolution
- [x] Implement a minimal in-memory `DomainRegistry` with a public `register()` function — self-registration pattern (decided in SPEC.md FR3): each `domains/*` package calls `register()` as a side effect of import; no static domain list in core or NEXUS
- [x] Typed "not found" result for unknown domain id lookups (no throw)
- [x] Typed error (`UnresolvedAgentError`) for `AgentDef` referencing an unregistered agent constructor, identifying domain + agent id
- [x] Statically verify (manual grep audit) zero imports from any `domains/*` path in `packages/core`

Deliverables:
- `packages/core` exports `DomainRegistry` interface + a minimal implementation
- No static cross-domain imports

### Phase 4: Unit Tests

**Agent:** tester
**Standards:** unit-testing, typescript-standards

Tasks:
- [x] Compile-time tests (zero-dependency `@ts-expect-error` assertions in `domain-config.type-tests.ts`, checked by `tsc --noEmit` — no `tsd`/`expectTypeOf` dependency needed) that a valid `DomainConfig` object literal type-checks
- [x] Compile-time test that a `DomainConfig` missing a required field fails to type-check
- [x] Compile-time test that a non-CSS field added to `ThemeVars` fails to type-check
- [x] Runtime unit tests for `DomainRegistry`: register + resolve by id; resolve unknown domain id; resolve `AgentDef` with missing constructor (4 tests, `domain-registry.test.ts`, vitest)
- [x] Minimal fixture `DomainConfig`/`FixtureAgent` (extends `BaseAgent`) used across `DomainRegistry` tests

Deliverables:
- Test suite passing for all Phase 1–3 deliverables
- Coverage of every Acceptance Criterion (AC1–AC6) in SPEC.md

### Phase 5: Domain Documentation

**Standards:** domain-population (per sdd:domain-population skill)

Tasks:
- [x] Add glossary terms (AgentDef, DomainRegistry) to `specs/domain/glossary.md` — BaseAgent/AgentInput/AgentOutput/DomainConfig already existed there (pre-dated this change); confirmed/reconciled rather than re-added
- [x] Create `specs/domain/definitions/base-agent.md`
- [x] Create `specs/domain/definitions/domain-config.md`
- [x] Create `specs/domain/definitions/domain-registry.md`
- [x] Update `specs/architecture/overview.md` with the domain registration flow section (L3 — Agent Fleet)

Deliverables:
- All "Specs Directory Changes" in SPEC.md applied exactly as declared

### Phase 6: Review

**Agent:** reviewer

Tasks:
- [x] Spec compliance review against all 6 acceptance criteria — AC1–AC6 all satisfied (AC2/AC4 via compile-time `@ts-expect-error` tests; AC3 via grep audit; AC5 via `AgentOutput.cited_chunks`/`response`; AC6 via clean `tsc --noEmit`)
- [x] Confirm zero domain-specific logic/imports in packages/core (AC1, AC3) — grep audit clean
- [x] Confirm `tsc --noEmit` passes with no `any` in the new types (AC6) — clean, zero `any` occurrences
- [x] Confirm specs/ changes match SPEC.md's declared Specs Directory Changes exactly — all 5 declared paths (glossary.md, overview.md, 3 new definition files) match

## Expected Files

### Files to Create

| File | Component | Description |
|------|-----------|-------------|
| `packages/core/src/agent/base-agent.ts` | packages/core | `BaseAgent` interface |
| `packages/core/src/agent/agent-input.ts` | packages/core | `AgentInput` type |
| `packages/core/src/agent/agent-output.ts` | packages/core | `AgentOutput` type |
| `packages/core/src/agent/memory-types.ts` | packages/core | `StudentProfile`, `Message`, `ContentChunk`, `EpisodicMemory`, `MasteryDelta` supporting types |
| `packages/core/src/domain/domain-config.ts` | packages/core | `DomainConfig`, `AgentDef`, `EvalRubric`, `ThemeVars`, `Rule` |
| `packages/core/src/domain/domain-registry.ts` | packages/core | `DomainRegistry` interface + minimal implementation |
| `packages/core/src/index.ts` | packages/core | Public exports (may already exist — modify if so) |
| `specs/domain/definitions/base-agent.md` | docs | Domain definition |
| `specs/domain/definitions/domain-config.md` | docs | Domain definition |
| `specs/domain/definitions/domain-registry.md` | docs | Domain definition |

### Files to Modify

| File | Component | Description |
|------|-----------|-------------|
| `specs/domain/glossary.md` | docs | Add BaseAgent, DomainConfig, AgentDef, DomainRegistry terms |
| `specs/architecture/overview.md` | docs | Add core contracts / domain registration section |

## Implementation State

### Current Phase

- **Phase:** Complete (all 6 phases)
- **Status:** complete
- **Last Updated:** 2026-07-10

### Completed Phases

| Phase | Completed | Notes |
|-------|-----------|-------|
| 1 | [x] | BaseAgent conformed to pre-existing glossary shape (abstract class, 4 methods) |
| 2 | [x] | |
| 3 | [x] | |
| 4 | [x] | `tsc --noEmit` clean; 4/4 vitest tests pass |
| 5 | [x] | Glossary/overview reconciled rather than blindly appended to |
| 6 | [x] | Self-review against all 6 ACs passed; ready for user review |

### Actual Files Changed

| File | Action | Phase | Notes |
|------|--------|-------|-------|
| `tsconfig.base.json` | Create | 1 (infra) | Root shared strict TS config — no tooling existed prior to this change |
| `package.json` | Modify | 1 (infra) | Added `typecheck`/`test` workspace scripts + `typescript`/`vitest` devDependencies |
| `packages/core/tsconfig.json` | Create | 1 (infra) | Extends root base config |
| `packages/core/vitest.config.ts` | Create | 1 (infra) | |
| `packages/core/package.json` | Modify | 1 (infra) | Added `typecheck`/`test` scripts |
| `packages/core/src/agent/memory-types.ts` | Create | 1 | `StudentProfile`, `Message`, `ContentChunk`, `EpisodicMemory`, `MasteryDelta` |
| `packages/core/src/agent/agent-input.ts` | Create | 1 | Conformed to pre-existing glossary field names/casing |
| `packages/core/src/agent/agent-output.ts` | Create | 1 | |
| `packages/core/src/agent/base-agent.ts` | Create | 1 | Conformed to pre-existing glossary method surface (abstract class) |
| `packages/core/src/domain/domain-config.ts` | Create | 2 | `DomainConfig`, `AgentDef`, `EvalRubric`, `EvalCriterion`, `ThemeVars`, `Rule` |
| `packages/core/src/domain/domain-registry.ts` | Create | 3 | `DomainRegistry`, `createDomainRegistry`, `UnresolvedAgentError` |
| `packages/core/src/index.ts` | Create | 1–3 | Public exports |
| `packages/core/src/domain/domain-config.type-tests.ts` | Create | 4 | Compile-time `@ts-expect-error` assertions (AC2, AC4) |
| `packages/core/src/domain/domain-registry.test.ts` | Create | 4 | 4 vitest tests |
| `specs/domain/glossary.md` | Modify | 5 | Added AgentDef, DomainRegistry entries |
| `specs/architecture/overview.md` | Modify | 5 | L3 section: DomainRegistry + self-registration flow |
| `specs/domain/definitions/base-agent.md` | Create | 5 | |
| `specs/domain/definitions/domain-config.md` | Create | 5 | |
| `specs/domain/definitions/domain-registry.md` | Create | 5 | |

### Blockers

- (none currently — two blockers surfaced and were resolved during implementation, see below)

### Resolved During Implementation

- **No TypeScript tooling existed in the repo.** Bootstrapped minimal infra (root `tsconfig.base.json`, `typescript`/`vitest` devDependencies, per-package config) after user confirmed scope — see SPEC.md Gaps & Assumptions.
- **Pre-existing `specs/domain/glossary.md`/`overview.md` conflicted with the originally-approved FR1 field shapes.** User decided: conform the implementation to the existing glossary (source of truth) rather than the reverse. `AgentInput` and `BaseAgent` were reworked accordingly; SPEC.md FR1 updated to match the as-built shape.

### Resource Usage

| Phase | Tokens (Input) | Tokens (Output) | Turns | Duration | Notes |
|-------|-----------------|------------------|-------|----------|-------|
| 1 | - | - | - | | |
| 2 | - | - | - | | |
| 3 | - | - | - | | |
| 4 | - | - | - | | |
| 5 | - | - | - | | |
| 6 | - | - | - | | |
| **Total** | **-** | **-** | **-** | **-** | |

## Dependencies

- None external. Internally, this change unblocks the paused `core-data-schema` epic.

## Risks

| Risk | Mitigation |
|------|------------|
| `packages/core` isn't registered as an SDD component, so future changes touching it won't get automatic phase generation | Track as an open question in SPEC.md; consider a tech-pack/settings update if a pattern emerges across packages/ui, packages/memory, packages/eval |
| Contract is declared "immutable" but nothing enforces that beyond convention | Consider a lint rule or CI check in a later change once real consumers exist |
