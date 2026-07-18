---
title: LangGraph State Machine - Implementation Plan
change: langgraph-state-machine
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-17
sdd_version: 7.3.0
---

## Overview

Implementation plan for: LangGraph State Machine

Specification: [SPEC.md](./SPEC.md)

## Affected Components

- apps/backend (existing, untracked as an SDD component)

## Prerequisites

- `nexus-supervisor` — complete. Provides `DomainConfig`, `DomainRegistry`, MCAT registration.

## Implementation Phases

### Phase 1: Graph State + Builder

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [x] Add `langgraph` to `apps/backend/pyproject.toml` dependencies (installed: 1.2.9)
- [x] Verified the real API against a minimal throwaway script before writing production code: `StateGraph` accepts a Pydantic model directly; node functions return partial-update `dict`s (not full `model_copy`'d state — nested Pydantic objects survive the round-trip as real instances, confirmed); `add_conditional_edges(START, fn, mapping)` gives a dynamic entry point; `aget_state(config)` returns an empty-but-truthy-checkable snapshot on a fresh thread
- [x] Create `apps/backend/nexus/graph_state.py`: `GraphState`, `MAX_HOPS` (FR3)
- [x] Create `apps/backend/nexus/graph_builder.py`: `build_graph(domain_config, registry)` — dynamic nodes (FR1), handoff routing + context folding (FR2), escalation short-circuit (FR4)

Deliverables:
- `build_graph` implements FR1, FR2, FR3, FR4 — SPEC.md's original sketch held up against the real API, no corrections needed this time

### Phase 2: Checkpointing + Turn Runner

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [x] Wire `MemorySaver` checkpointer into `build_graph`'s `.compile(...)` (FR5)
- [x] Create `apps/backend/nexus/turn_runner.py`: `run_turn(...)` (FR6)

Deliverables:
- `run_turn` implements FR5, FR6

### Phase 3: Integration Tests

**Standards:** N/A (pytest)

Tasks:
- [x] `test_graph_builder.py`: dynamic node sets with two different fake domain configs (AC1) — via `compiled_graph.get_graph().nodes`
- [x] `test_turn_runner.py`: real ARIA→MIRA handoff, verify no-cold-start context folding (AC2)
- [x] `test_turn_runner.py`: pathological always-handoff fake config, verify `MAX_HOPS` termination (AC3)
- [x] `test_turn_runner.py`: simultaneous `risk_level='high'` + `suggested_handoff` on one real ARIA output, verify escalation wins (AC4)
- [x] `test_turn_runner.py`: two sequential turns, same session, verify cross-turn checkpoint continuity (AC5)

Deliverables:
- Full pytest suite passing (54/54 — 49 existing + 5 new), covering AC1–AC5, using real ARIA/MIRA/QUINN (no mocks needed)

### Phase 4: Review

**Standards:** N/A (manual)

Tasks:
- [x] Spec compliance review against all 5 acceptance criteria — all satisfied
- [x] Confirm full existing test suite (ARIA/MIRA/QUINN + litellm-gateway + nexus-supervisor) still passes unchanged — confirmed

## Expected Files

### Files to Create

| File | Component | Description |
|------|-----------|--------------|
| `apps/backend/nexus/graph_state.py` | apps/backend | `GraphState`, `MAX_HOPS` |
| `apps/backend/nexus/graph_builder.py` | apps/backend | `build_graph` |
| `apps/backend/nexus/turn_runner.py` | apps/backend | `run_turn` |
| `apps/backend/tests/test_graph_builder.py` | apps/backend | |
| `apps/backend/tests/test_turn_runner.py` | apps/backend | |

### Files to Modify

| File | Description |
|------|-------------|
| `apps/backend/pyproject.toml` | Add `langgraph` dependency |

## Implementation State

### Current Phase

- **Phase:** Complete (all 4 phases)
- **Status:** complete
- **Last Updated:** 2026-07-17

### Completed Phases

| Phase | Completed | Notes |
|-------|-----------|-------|
| 1 | [x] | Real LangGraph 1.2.9 API verified via a throwaway script before production code; SPEC.md's sketch held up |
| 2 | [x] | |
| 3 | [x] | All 5 tests passed on first run — real ARIA/MIRA cascade, real checkpointing |
| 4 | [x] | |

### Actual Files Changed

| File | Action | Phase | Notes |
|------|--------|-------|-------|
| `apps/backend/nexus/graph_state.py` | Create | 1 | |
| `apps/backend/nexus/graph_builder.py` | Create | 1 | |
| `apps/backend/nexus/turn_runner.py` | Create | 2 | |
| `apps/backend/tests/test_graph_builder.py` | Create | 3 | |
| `apps/backend/tests/test_turn_runner.py` | Create | 3 | |
| `apps/backend/pyproject.toml` | Modify | 1 | Added `langgraph` dependency |

### Blockers

- (none)

## Dependencies

- `nexus-supervisor`

## Risks

| Risk | Mitigation |
|------|------------|
| Exact LangGraph API (conditional entry points, checkpointer config surface) may differ from what SPEC.md sketches | Verified directly against the real installed `langgraph` package during implementation (no credentials needed for this); SPEC.md updated to match if the real API differs, same pattern as prior changes |
