---
title: MIRA — Motivation & Resilience Coach (MCAT) - Implementation Plan
change: mira-agent
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-15
sdd_version: 7.3.0
---

## Overview

Implementation plan for: MIRA — Motivation & Resilience Coach (MCAT)

Specification: [SPEC.md](./SPEC.md)

## Affected Components

<!-- Same gap as changes/2026/07/10/aria-agent/ -- apps/backend has no SDD component
     type in the active tech pack. Phases hand-authored. -->
- apps/backend (existing, untracked as an SDD component)

## Prerequisites

- `changes/2026/07/10/aria-agent/` — complete. Reuses `BaseAgent`, contract mirrors, `PromptRegistryClient` as-is (no changes to `_contracts/` or `prompt_registry/`).

## Implementation Phases

### Phase 1: MIRA Prompt

**Component:** apps/backend / docs
**Standards:** N/A

Tasks:
- [x] Create `domains/mcat/prompts/mira_v1.md` — MIRA's authored system prompt: identity, empathy-first method (acknowledge → validate effort → one concrete strategy), growth-mindset framing, not-a-therapist boundary, prohibited behaviors

Deliverables:
- `FilePromptRegistryClient(domain="mcat").get_prompt('mira', 'v1')` returns the file's contents (verified via `test_prompt_registry.py`)

### Phase 2: MIRA Agent

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [x] Create `apps/backend/domains/mcat/agents/mira.py` extending `BaseAgent`
- [x] Implement handoff-cause lookup: most recent `episodic_context` entry by `occurredAt` (FR2)
- [x] Implement acknowledge → validate-effort → one-strategy response structure (AC1, AC2)
- [x] Implement `DistressEstimator`/`RecoverySignalClassifier` protocols + interim keyword heuristics (`KeywordDistressEstimator`, `KeywordRecoverySignalClassifier`)
- [x] Implement handoff rule: recovery signals in last 2 user messages → `suggested_handoff = 'aria'` (AC3)
- [x] Implement handoff rule: distress > 0.85 → `risk_level = 'high'` (AC4), taking priority over a simultaneous recovery signal (AC6)
- [x] Implement invariant: `suggested_handoff` never `'quinn'` (AC5)
- [x] Implement prohibited-behavior guards: no minimizing language, no MCAT content, no outcome promises (AC7)
- [x] Wire `fetch_prompt()` to the existing `PromptRegistryClient` with `agent_id='mira'`

Deliverables:
- `mira.py` implements all of FR1, FR3, FR4

### Phase 3: Unit Tests

**Standards:** N/A (pytest)

Tasks:
- [x] `test_mira.py`: acknowledges specific struggle from `episodic_context` (AC1)
- [x] `test_mira.py`: validates effort + exactly one strategy (AC2)
- [x] `test_mira.py`: recovery signals → `aria` handoff (AC3)
- [x] `test_mira.py`: distress > 0.85 → `risk_level == 'high'` (AC4)
- [x] `test_mira.py`: `suggested_handoff` never `'quinn'` across varied inputs (AC5)
- [x] `test_mira.py`: distress + recovery simultaneously → `risk_level == 'high'` wins (AC6)
- [x] `test_mira.py`: no minimizing/content-pushing/outcome-promise language (AC7)
- [x] Re-run full existing suite (`test_health.py`, `test_agent_io_contracts.py`, `test_aria.py`) — confirmed 13/13 still pass (AC8)
- [x] Bonus (not in original scope, low-cost): added `test_file_prompt_registry_client_reads_mira_prompt` to `test_prompt_registry.py`

Deliverables:
- Full pytest suite passing — 21/21 (existing 13 + 8 new)

### Phase 4: Domain Documentation

**Standards:** domain-population (per sdd:domain-population skill)

Tasks:
- [x] Create `specs/domain/definitions/mira.md`
- [x] No glossary.md changes — MIRA already documented there

Deliverables:
- `specs/domain/definitions/mira.md` created, matching SPEC.md's declared Specs Directory Changes

### Phase 5: Review

**Standards:** N/A (manual — no Python verification agent in the active tech pack)

Tasks:
- [x] Spec compliance review against all 8 acceptance criteria — all satisfied
- [x] Confirm full pytest suite passes (existing + new) — 21/21
- [x] Confirm `specs/` changes match SPEC.md's declared Specs Directory Changes exactly — only `specs/domain/definitions/mira.md` added, matches
- [x] Confirmed no stray `.venv`/`__pycache__` files via `git ls-files --others --exclude-standard`

## Expected Files

### Files to Create

| File | Component | Description |
|------|-----------|--------------|
| `domains/mcat/prompts/mira_v1.md` | docs/prompt | MIRA's system prompt |
| `apps/backend/domains/mcat/agents/mira.py` | apps/backend | MIRA implementation |
| `apps/backend/tests/test_mira.py` | apps/backend | MIRA tests |
| `specs/domain/definitions/mira.md` | docs | Domain definition |

### Files to Modify

None declared.

## Implementation State

### Current Phase

- **Phase:** Complete (all 5 phases)
- **Status:** complete
- **Last Updated:** 2026-07-15

### Completed Phases

| Phase | Completed | Notes |
|-------|-----------|-------|
| 1 | [x] | |
| 2 | [x] | |
| 3 | [x] | 21/21 tests passing |
| 4 | [x] | |
| 5 | [x] | Self-review against all 8 ACs passed; ready for user review |

### Actual Files Changed

| File | Action | Phase | Notes |
|------|--------|-------|-------|
| `domains/mcat/prompts/mira_v1.md` | Create | 1 | MIRA's authored system prompt |
| `apps/backend/domains/mcat/agents/mira.py` | Create | 2 | MIRA implementation (FR1, FR3, FR4) |
| `apps/backend/tests/test_mira.py` | Create | 3 | 7 tests covering AC1–AC7 |
| `apps/backend/tests/test_prompt_registry.py` | Modify | 3 | Added MIRA prompt-read test (bonus, low-cost) |
| `specs/domain/definitions/mira.md` | Create | 4 | |

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
| **Total** | **-** | **-** | **-** | **-** | |

## Dependencies

- `changes/2026/07/10/aria-agent/` — reused as-is.

## Risks

| Risk | Mitigation |
|------|------------|
| `episodic_context` reuse for handoff-context is a stopgap, not a real contract field | Tracked as an open question in SPEC.md; revisit if a third agent needs the same pattern |
| Distress/recovery heuristics are crude placeholders | Isolated behind `DistressEstimator`/`RecoverySignalClassifier` protocols for easy replacement, same pattern as ARIA |
