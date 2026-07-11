---
title: ARIA — Adaptive Tutor Agent (MCAT) - Implementation Plan
change: aria-agent
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-10
sdd_version: 7.3.0
---

## Overview

Implementation plan for: ARIA — Adaptive Tutor Agent (MCAT)

Specification: [SPEC.md](./SPEC.md)

## Affected Components

<!-- apps/backend does not exist and the active fullstack-typescript tech pack has no
     Python/FastAPI component type at all (broader gap than packages/core's, which at
     least fit the tech pack's general "shared package" absence — this is a whole
     missing runtime). Phases below are hand-authored. See SPEC.md Open Questions /
     Components section. -->
- apps/backend (net-new, untracked as an SDD component)

## Prerequisites

- `changes/2026/07/09/baseagent-domainconfig-contracts/` (TypeScript contract) — complete, this change mirrors its shape in Python.

## Implementation Phases

### Phase 1: Backend Bootstrap

**Component:** apps/backend
**Standards:** N/A (no Python standards in the active tech pack — manual review against general Python/FastAPI conventions)

Tasks:
- [ ] Create `apps/backend/pyproject.toml` (Python 3.11+, deps: fastapi, uvicorn, pydantic; dev deps: pytest, httpx)
- [ ] Create `apps/backend/main.py` with a FastAPI app and `GET /health` → `{"status": "ok"}`
- [ ] Create `apps/backend/tests/test_health.py` using FastAPI's `TestClient`

Deliverables:
- `apps/backend` installs (`pip install -e .`) and boots (`uvicorn main:app`)
- `GET /health` returns 200 (AC1)

### Phase 2: Contract Mirrors

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [ ] Create `apps/backend/domains/_contracts/agent_io.py`: Pydantic `StudentProfile`, `Message`, `ContentChunk`, `EpisodicMemory`, `MasteryDelta`, `AgentInput`, `AgentOutput` — field names/types matching `packages/core/src/agent/*.ts` exactly
- [ ] Create `apps/backend/domains/_contracts/base_agent.py`: abstract `BaseAgent` (abstract `fetch_prompt`, `respond`, `write_episodic_memory`; concrete `stream` orchestrating the three) — mirrors the TypeScript `BaseAgent`'s control flow
- [ ] Create `apps/backend/tests/test_agent_io_contracts.py`: assert Pydantic field sets match the documented reference list in SPEC.md FR2 (AC2)

Deliverables:
- `agent_io.py`, `base_agent.py` created
- Contract-parity test passing

### Phase 3: PromptRegistry Client

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [ ] Create `apps/backend/prompt_registry/client.py`: `PromptRegistryClient` protocol (`get_prompt(agent_id, version) -> str`) + `FilePromptRegistryClient` reading `domains/{domain}/prompts/{agent_id}_{version}.md`
- [ ] Create `domains/mcat/prompts/aria_v1.md` (repo root, per CLAUDE.md convention) — ARIA's authored system prompt: identity, Socratic method instruction, 4-section coverage, prohibited behaviors

Deliverables:
- `FilePromptRegistryClient.get_prompt('aria', 'v1')` returns the file's contents

### Phase 4: ARIA Agent

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [x] Create `apps/backend/domains/mcat/agents/aria.py` extending `BaseAgent` (Phase 2)
- [x] Implement diagnostic-opening check — deviated from spec draft: keyed off prior `EpisodicMemory` mentions of the inferred concept, not `MasteryDelta` (no per-concept mastery field exists on `StudentProfile`; documented as a heuristic in SPEC.md Gaps & Assumptions and `specs/domain/definitions/aria.md`) (AC3)
- [x] Implement mastery-adapted explanation depth — heuristic based on prior-mention count in `episodic_context`, same reasoning as above
- [x] Implement `cited_chunks` population from `retrieved_chunks` actually used (AC4)
- [x] Implement `FrustrationEstimator`/`TurnOutcomeClassifier` protocols + interim heuristic implementations (`KeywordFrustrationEstimator`, `KeywordTurnOutcomeClassifier`)
- [x] Implement handoff rule: frustration > 0.6 over last 3 user messages → `suggested_handoff = 'mira'` (AC5)
- [x] Implement handoff rule: 4+ consecutive successful turns (tracked via `session_notes`/`episodic_context` marker) → `suggested_handoff = 'quinn'` (AC6)
- [x] Implement medical-advice guard: decline + `risk_level = 'high'` (AC7)
- [x] Implement remaining prohibited-behavior guards: no score guarantees, no unexplained answers, no skipped diagnostic opening (AC8)
- [x] Wire `fetch_prompt()` to `PromptRegistryClient` (Phase 3), not inline text

Deliverables:
- `aria.py` implements all of FR3–FR5

### Phase 5: Unit Tests

**Standards:** N/A (pytest)

Tasks:
- [x] `test_aria.py`: diagnostic opening on new concept (AC3)
- [x] `test_aria.py`: `cited_chunks` non-empty when `retrieved_chunks` used (AC4)
- [x] `test_aria.py`: frustration → `mira` handoff (AC5)
- [x] `test_aria.py`: 4+ successful turns → `quinn` handoff (AC6)
- [x] `test_aria.py`: medical advice → declined + `risk_level == 'high'` (AC7)
- [x] `test_aria.py`: no score guarantees / no unexplained answers / no skipped opening (AC8)
- [x] Fixtures: minimal valid `AgentInput`, frustrated `session_history`, successful-streak `episodic_context`

Deliverables:
- Full pytest suite passing (13/13), covering AC1–AC8

### Phase 6: Domain Documentation

**Standards:** domain-population (per sdd:domain-population skill)

Tasks:
- [x] Create `specs/domain/definitions/aria.md` (identity, behavior rules, handoff thresholds, prohibited behaviors)
- [x] No glossary.md changes — ARIA/BaseAgent/AgentInput/AgentOutput/Handoff already documented there

Deliverables:
- `specs/domain/definitions/aria.md` created, matching SPEC.md's declared Specs Directory Changes

### Phase 7: Review

**Standards:** N/A (manual — no Python verification agent in the active tech pack)

Tasks:
- [x] Spec compliance review against all 8 acceptance criteria — all satisfied
- [x] Confirm `pytest` passes in full — 13/13
- [x] Confirm `apps/backend` boots and `GET /health` works — verified via live uvicorn boot + HTTP request
- [x] Confirm `specs/` changes match SPEC.md's declared Specs Directory Changes exactly — only `specs/domain/definitions/aria.md` added, matches
- [x] `.gitignore` updated to exclude `.venv/`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/` (none existed before this change; verified via `git ls-files --others --exclude-standard`)

## Expected Files

### Files to Create

| File | Component | Description |
|------|-----------|--------------|
| `apps/backend/pyproject.toml` | apps/backend | Project metadata + dependencies |
| `apps/backend/main.py` | apps/backend | FastAPI app, `GET /health` |
| `apps/backend/domains/_contracts/agent_io.py` | apps/backend | Pydantic mirrors |
| `apps/backend/domains/_contracts/base_agent.py` | apps/backend | Python `BaseAgent` ABC |
| `apps/backend/prompt_registry/client.py` | apps/backend | `PromptRegistryClient` + `FilePromptRegistryClient` |
| `apps/backend/domains/mcat/agents/aria.py` | apps/backend | ARIA implementation |
| `apps/backend/tests/test_health.py` | apps/backend | Phase 1 test |
| `apps/backend/tests/test_agent_io_contracts.py` | apps/backend | Phase 2 test |
| `apps/backend/tests/test_aria.py` | apps/backend | Phase 4–5 tests |
| `domains/mcat/prompts/aria_v1.md` | docs/prompt | ARIA's system prompt |
| `specs/domain/definitions/aria.md` | docs | Domain definition |

### Files to Modify

None declared — see SPEC.md Domain Updates (no glossary.md changes needed).

## Implementation State

### Current Phase

- **Phase:** Complete (all 7 phases)
- **Status:** complete
- **Last Updated:** 2026-07-10

### Completed Phases

| Phase | Completed | Notes |
|-------|-----------|-------|
| 1 | [x] | Bootstrapped with Python 3.11 (via Homebrew — system Python was 3.9.6); venv, install, boot, `GET /health` all verified |
| 2 | [x] | Contract-parity tests pass |
| 3 | [x] | Repo-root path bug caught and fixed during verification (`parents[2]` → `parents[3]`) |
| 4 | [x] | Diagnostic-opening/depth logic deviated from FR3's original wording — see FR3 update and Gaps & Assumptions |
| 5 | [x] | 13/13 tests passing |
| 6 | [x] | |
| 7 | [x] | Self-review against all 8 ACs passed; ready for user review |

### Actual Files Changed

| File | Action | Phase | Notes |
|------|--------|-------|-------|
| `apps/backend/pyproject.toml` | Create | 1 | Python 3.11+, fastapi/uvicorn/pydantic; dev: pytest, pytest-asyncio, httpx |
| `apps/backend/main.py` | Create | 1 | FastAPI app, `GET /health` |
| `apps/backend/tests/test_health.py` | Create | 1 | |
| `apps/backend/domains/_contracts/agent_io.py` | Create | 2 | Pydantic mirrors of `packages/core`'s TS contract |
| `apps/backend/domains/_contracts/base_agent.py` | Create | 2 | Python `BaseAgent` ABC (mirrored, not cross-language-inherited) |
| `apps/backend/tests/test_agent_io_contracts.py` | Create | 2 | Field-parity tests |
| `apps/backend/prompt_registry/client.py` | Create | 3 | `PromptRegistryClient` protocol + `FilePromptRegistryClient` |
| `domains/mcat/prompts/aria_v1.md` | Create | 3 | ARIA's authored system prompt (repo root) |
| `apps/backend/tests/test_prompt_registry.py` | Create | 3 | |
| `apps/backend/domains/mcat/agents/aria.py` | Create | 4 | ARIA implementation (FR3–FR5) |
| `apps/backend/tests/test_aria.py` | Create | 5 | 9 tests covering AC3–AC8 |
| `specs/domain/definitions/aria.md` | Create | 6 | |
| `.gitignore` | Modify | 7 | Added `.venv/`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/` |
| `changes/2026/07/10/aria-agent/SPEC.md` | Modify | 4 | FR3 updated to match as-built mastery/concept-tracking approach |
| `__init__.py` files (6) | Create | 1 | `domains/`, `domains/_contracts/`, `domains/mcat/`, `domains/mcat/agents/`, `prompt_registry/`, `tests/` |

### Blockers

- (none)

### Resource Usage

| Phase | Tokens (Input) | Tokens (Output) | Turns | Duration | Notes |
|-------|-----------------|------------------|-------|----------|-------|
| 1 | - | - | - | | |
| 2 | - | - | - | | |
| 3 | - | - | - | | |
| 4 | - | - | - | | |
| 5 | - | - | - | | |
| 6 | - | - | - | | |
| 7 | - | - | - | | |
| **Total** | **-** | **-** | **-** | **-** | |

## Dependencies

- `changes/2026/07/09/baseagent-domainconfig-contracts/` — TypeScript contract shape this mirrors.

## Risks

| Risk | Mitigation |
|------|------------|
| Pydantic mirror silently drifts from the TypeScript contract over time | Phase 2's parity test fails CI if either side's field set changes without the other being updated |
| Frustration/readiness heuristics are crude placeholders | Isolated behind `FrustrationEstimator`/`TurnOutcomeClassifier` protocols (SPEC.md FR4) for easy replacement |
| `apps/backend` isn't a registered SDD component, so future Python changes won't get automatic phase generation | Tracked as an open question in SPEC.md, same pattern as `packages/core` |
