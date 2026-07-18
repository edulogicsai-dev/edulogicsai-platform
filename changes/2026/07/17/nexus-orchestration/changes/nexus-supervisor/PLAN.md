---
title: NEXUS Supervisor - Implementation Plan
change: nexus-supervisor
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-17
sdd_version: 7.3.0
---

## Overview

Implementation plan for: NEXUS Supervisor

Specification: [SPEC.md](./SPEC.md)

## Affected Components

- apps/backend (existing, untracked as an SDD component)

## Prerequisites

- `litellm-gateway` — complete. Provides `LiteLLMGatewayClient` for `LiteLLMIntentClassifier`.
- ARIA, MIRA, QUINN (all complete) — the agents being registered.

## Implementation Phases

### Phase 1: Python DomainConfig Mirror + DomainRegistry

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [x] Create `apps/backend/domains/_contracts/domain_config.py`: `AgentDef`, `EvalCriterion`, `EvalRubric`, `Rule`, `DomainConfig` dataclasses (FR1)
- [x] Create `apps/backend/domains/_contracts/domain_registry.py`: `DomainRegistry`, `DomainLookupResult`, `UnresolvedAgentError`, module-level `registry` singleton (FR2)

Deliverables:
- Both modules created, matching TypeScript shape field-for-field

### Phase 2: MCAT Domain Registration

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [x] Create `apps/backend/domains/mcat/domain_config.py`: `MCAT_DOMAIN_CONFIG` with all 3 agents, self-registers on import (FR3)

Deliverables:
- Importing this module registers `'mcat'` with all 3 agents resolvable

### Phase 3: Intent Classification

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [x] Create `apps/backend/nexus/intent_classifier.py`: `IntentClassifier` protocol, `KeywordIntentClassifier`, `LiteLLMIntentClassifier` (FR4)

Deliverables:
- All 3 classes implemented per FR4

### Phase 4: AgentInput Assembly + Tenant Context

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [x] Create `apps/backend/nexus/supervisor.py`: `assemble_agent_input(...)` (FR5)
- [x] Create `apps/backend/nexus/tenant_context.py`: `set_tenant_context(conn, tenant_id)` (FR6) — **discovered during implementation:** the originally-sketched `SET LOCAL app.tenant_id = $1` is invalid Postgres syntax (SET doesn't support bind parameters); implemented via `set_config('app.tenant_id', $1, true)` instead, and SPEC.md FR6/AC7 updated to match

Deliverables:
- Both functions implemented per FR5/FR6

### Phase 5: Unit Tests

**Standards:** N/A (pytest)

Tasks:
- [x] `test_domain_config.py`: dataclass construction, field parity (AC1)
- [x] `test_domain_registry.py`: register/resolve/unresolved-agent (AC2, AC3) — reusing the MCAT registration
- [x] `test_intent_classifier.py`: `KeywordIntentClassifier` (AC4), `LiteLLMIntentClassifier` with mocked gateway (AC5)
- [x] `test_supervisor.py`: `assemble_agent_input(...)` (AC6)
- [x] `test_tenant_context.py`: `set_tenant_context` against a mock connection (AC7)
- [x] `test_no_domain_leakage.py`: grep-style audit for zero domain-specific references outside `domains/mcat/` (AC8) — caught and fixed one real violation in a *comment* in `intent_classifier.py` that named MCAT agents explicitly; reworded to stay domain-agnostic

Deliverables:
- Full pytest suite passing (49/49 — 38 existing + 11 new), covering AC1–AC8

### Phase 6: Review

**Standards:** N/A (manual)

Tasks:
- [x] Spec compliance review against all 8 acceptance criteria — all satisfied
- [x] Confirm zero domain-specific logic in `domains/_contracts/`/`nexus/` (AC8) — verified via automated test, not just eyeballing
- [x] Confirm full existing ARIA/MIRA/QUINN test suite (32 tests) still passes unchanged — confirmed (38 total after litellm-gateway, all still passing)

## Expected Files

### Files to Create

| File | Component | Description |
|------|-----------|--------------|
| `apps/backend/domains/_contracts/domain_config.py` | apps/backend | Python `DomainConfig` mirror |
| `apps/backend/domains/_contracts/domain_registry.py` | apps/backend | `DomainRegistry` |
| `apps/backend/domains/mcat/domain_config.py` | apps/backend | MCAT registration |
| `apps/backend/nexus/__init__.py` | apps/backend | Package init |
| `apps/backend/nexus/intent_classifier.py` | apps/backend | Intent classification |
| `apps/backend/nexus/supervisor.py` | apps/backend | `assemble_agent_input` |
| `apps/backend/nexus/tenant_context.py` | apps/backend | `set_tenant_context` |
| `apps/backend/tests/test_domain_config.py` | apps/backend | |
| `apps/backend/tests/test_domain_registry.py` | apps/backend | |
| `apps/backend/tests/test_intent_classifier.py` | apps/backend | |
| `apps/backend/tests/test_supervisor.py` | apps/backend | |
| `apps/backend/tests/test_tenant_context.py` | apps/backend | |

## Implementation State

### Current Phase

- **Phase:** Complete (all 6 phases)
- **Status:** complete
- **Last Updated:** 2026-07-17

### Completed Phases

| Phase | Completed | Notes |
|-------|-----------|-------|
| 1 | [x] | |
| 2 | [x] | |
| 3 | [x] | |
| 4 | [x] | Caught a real Postgres syntax bug (SET LOCAL doesn't take bind params) before it shipped |
| 5 | [x] | Caught real domain-leakage in a comment via the grep-audit test |
| 6 | [x] | |

### Actual Files Changed

| File | Action | Phase | Notes |
|------|--------|-------|-------|
| `apps/backend/domains/_contracts/domain_config.py` | Create | 1 | |
| `apps/backend/domains/_contracts/domain_registry.py` | Create | 1 | |
| `apps/backend/domains/mcat/domain_config.py` | Create | 2 | |
| `apps/backend/nexus/__init__.py` | Create | 3 | |
| `apps/backend/nexus/intent_classifier.py` | Create | 3 | |
| `apps/backend/nexus/supervisor.py` | Create | 4 | |
| `apps/backend/nexus/tenant_context.py` | Create | 4 | |
| `apps/backend/tests/test_domain_config.py` | Create | 5 | |
| `apps/backend/tests/test_domain_registry.py` | Create | 5 | |
| `apps/backend/tests/test_intent_classifier.py` | Create | 5 | |
| `apps/backend/tests/test_supervisor.py` | Create | 5 | |
| `apps/backend/tests/test_tenant_context.py` | Create | 5 | |
| `apps/backend/tests/test_no_domain_leakage.py` | Create | 5 | |

### Blockers

- (none)

## Dependencies

- `litellm-gateway`, ARIA, MIRA, QUINN.

## Risks

| Risk | Mitigation |
|------|------------|
| `LiteLLMIntentClassifier` never exercised against a real model | Unit-tested against a mocked gateway client; real exercise deferred to when credentials exist |
| Empty `theme: {}` may need real values before `apps/web` integration | Explicitly flagged in SPEC.md Gaps & Assumptions, not this epic's scope |
