---
title: QUINN — Practice Question Intelligence Agent (MCAT) - Implementation Plan
change: quinn-agent
type: feature
spec: ./SPEC.md
status: draft
created: 2026-07-15
sdd_version: 7.3.0
---

## Overview

Implementation plan for: QUINN — Practice Question Intelligence Agent (MCAT)

Specification: [SPEC.md](./SPEC.md)

## Affected Components

<!-- Same gap as prior MCAT agent changes -- apps/backend has no SDD component
     type in the active tech pack. Phases hand-authored. -->
- apps/backend (existing, untracked as an SDD component)

## Prerequisites

- `changes/2026/07/10/aria-agent/` — complete. Reuses `BaseAgent`, contract mirrors, `PromptRegistryClient`, frustration-heuristic pattern.
- `changes/2026/07/15/mira-agent/` — complete. Reuses the `episodic_context`/`session_notes` state-channel pattern.

## Implementation Phases

### Phase 1: QUINN Prompt

**Component:** apps/backend / docs
**Standards:** N/A

Tasks:
- [x] Create `domains/mcat/prompts/quinn_v1.md` — QUINN's authored system prompt: identity, one-question-at-a-time method, answer-before-explanation rule, distractor-analysis requirement, prohibited behaviors

Deliverables:
- `FilePromptRegistryClient(domain="mcat").get_prompt('quinn', 'v1')` returns the file's contents (verified via `test_prompt_registry.py`)

### Phase 2: Question/Answer State Machine + Generation

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [x] Create `apps/backend/domains/mcat/agents/quinn.py` extending `BaseAgent`
- [x] Implement `quinn_pending` marker encode/decode (concept, correct answer, distractor + reason, streak counters) via `session_notes`/`episodic_context` (FR1) — implemented as a JSON payload (`{prefix}` + `json.dumps(...)`), not the ad-hoc key=value string originally sketched in SPEC.md's Algorithms section, for robustness against special characters in chunk text
- [x] Implement `QuestionGenerator` protocol + `TemplatedQuestionGenerator` placeholder grounded in `retrieved_chunks` (FR2)
- [x] Implement difficulty bound via `episodic_context` mention-count proxy (same pattern as ARIA's mastery approximation) (FR2)
- [x] Implement "no pending question" branch: generate + present a question, withhold the answer, populate `cited_chunks` (AC1, AC3)
- [x] Implement "pending question found" branch: evaluate `message` against the stored correct answer, confirm correct/incorrect, run full distractor analysis, update streak counters (FR3, AC2)
- [x] Reused ARIA's `KeywordFrustrationEstimator`/`MEDICAL_ADVICE_PATTERNS` directly (import from `domains.mcat.agents.aria`) rather than duplicating, per FR4/FR5's "same as ARIA's" requirement

Deliverables:
- `quinn.py` implements FR1–FR3

### Phase 3: Handoff Rules

**Component:** apps/backend
**Standards:** N/A

Tasks:
- [x] Implement frustration reuse (same threshold/shape as ARIA's, over last 3 messages) → `suggested_handoff = 'mira'` (AC6)
- [x] Implement 3+ consecutive wrong on same concept → `suggested_handoff = 'aria'` (AC4)
- [x] Implement 5+ questions at 80%+ accuracy → `suggested_handoff = 'scout'` (AC5)
- [x] Implement priority order: frustration > consecutive-wrong > accuracy milestone (AC6)
- [x] Implement medical-advice guard, same as ARIA (AC7) — additionally preserves any pending-question state unchanged when triggered, rather than losing it (not explicitly required by an AC, but a direct consequence of FR5's "independent of pending-question state")
- [x] Implement prohibited-behavior guards: no answer-before-attempt, no skipped distractor analysis, no over-tier question (AC8)

Deliverables:
- `quinn.py` implements FR4–FR5

### Phase 4: Unit Tests

**Standards:** N/A (pytest)

Tasks:
- [x] `test_quinn.py`: fresh question presented, answer withheld, `cited_chunks` populated (AC1, AC3)
- [x] `test_quinn.py`: pending question + correct answer → full distractor analysis (AC2)
- [x] `test_quinn.py`: pending question + incorrect answer → full distractor analysis (AC2)
- [x] `test_quinn.py`: 3 consecutive wrong → `aria` handoff (AC4)
- [x] `test_quinn.py`: 5+ questions, 80%+ accuracy → `scout` handoff (AC5)
- [x] `test_quinn.py`: frustration wins over simultaneous wrong-streak/accuracy condition (AC6)
- [x] `test_quinn.py`: medical advice → declined + `risk_level == 'high'` (AC7) + preserves pending-question state (bonus test, not a separate AC)
- [x] `test_quinn.py`: no answer-before-attempt / no skipped distractor analysis when handing off (AC8)
- [x] Re-run full existing suite (ARIA + MIRA, 21 tests) — confirmed still passing (AC9)
- [x] Added `test_file_prompt_registry_client_reads_quinn_prompt` to `test_prompt_registry.py` (bonus, same as MIRA change's pattern)

Deliverables:
- Full pytest suite passing — 32/32 (existing 21 + 11 new)

### Phase 5: Domain Documentation

**Standards:** domain-population (per sdd:domain-population skill)

Tasks:
- [x] Create `specs/domain/definitions/quinn.md`
- [x] No glossary.md changes — QUINN already documented there

Deliverables:
- `specs/domain/definitions/quinn.md` created, matching SPEC.md's declared Specs Directory Changes

### Phase 6: Review

**Standards:** N/A (manual — no Python verification agent in the active tech pack)

Tasks:
- [x] Spec compliance review against all 9 acceptance criteria — all satisfied
- [x] Confirm full pytest suite passes (existing + new) — 32/32
- [x] Confirm `specs/` changes match SPEC.md's declared Specs Directory Changes exactly — only `specs/domain/definitions/quinn.md` added, matches
- [x] Confirmed no `Any` typing usage, no stray `.venv`/`__pycache__` files

## Expected Files

### Files to Create

| File | Component | Description |
|------|-----------|--------------|
| `domains/mcat/prompts/quinn_v1.md` | docs/prompt | QUINN's system prompt |
| `apps/backend/domains/mcat/agents/quinn.py` | apps/backend | QUINN implementation |
| `apps/backend/tests/test_quinn.py` | apps/backend | QUINN tests |
| `apps/backend/tests/test_prompt_registry.py` | apps/backend | Modify — add QUINN prompt-read test |
| `specs/domain/definitions/quinn.md` | docs | Domain definition |

## Implementation State

### Current Phase

- **Phase:** Complete (all 6 phases)
- **Status:** complete
- **Last Updated:** 2026-07-15

### Completed Phases

| Phase | Completed | Notes |
|-------|-----------|-------|
| 1 | [x] | |
| 2 | [x] | Marker format implemented as JSON, not the ad-hoc string sketched in SPEC.md — updated to match |
| 3 | [x] | Reused ARIA's frustration heuristic/medical-advice patterns directly via import, not duplicated |
| 4 | [x] | 32/32 tests passing; one flawed test assertion caught and fixed during verification |
| 5 | [x] | |
| 6 | [x] | Self-review against all 9 ACs passed; ready for user review |

### Actual Files Changed

| File | Action | Phase | Notes |
|------|--------|-------|-------|
| `domains/mcat/prompts/quinn_v1.md` | Create | 1 | QUINN's authored system prompt |
| `apps/backend/domains/mcat/agents/quinn.py` | Create | 2–3 | State machine, question generation, handoff rules (FR1–FR5) |
| `apps/backend/tests/test_quinn.py` | Create | 4 | 10 tests covering AC1–AC8 |
| `apps/backend/tests/test_prompt_registry.py` | Modify | 4 | Added QUINN prompt-read test |
| `specs/domain/definitions/quinn.md` | Create | 5 | |
| `changes/2026/07/15/quinn-agent/SPEC.md` | Modify | 2 | Algorithms section updated: JSON marker format, not the originally-sketched key=value string |

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
| **Total** | **-** | **-** | **-** | **-** | |

## Dependencies

- `changes/2026/07/10/aria-agent/`, `changes/2026/07/15/mira-agent/` — both reused as-is.

## Risks

| Risk | Mitigation |
|------|------------|
| `session_notes`/`episodic_context` state encoding is now used by 3 agents for 3 different purposes | Raised as an Open Question in SPEC.md — worth formalizing into a typed field if a 4th agent needs it |
| Templated question generation is not exam-quality | Explicitly out of scope; isolated behind `QuestionGenerator` protocol for future LLM-backed replacement |
| Priority-order edge case (all 3 handoff conditions at once) is unlikely but must resolve deterministically | Explicit priority order tested in AC6 |
