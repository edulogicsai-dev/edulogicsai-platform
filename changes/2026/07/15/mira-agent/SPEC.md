---
title: MIRA — Motivation & Resilience Coach (MCAT)
type: feature
status: active
domain: mcat
issue: TBD
created: 2026-07-15
updated: 2026-07-15
sdd_version: 7.3.0
affected_components: []
---

## Overview

Implement MIRA — the Motivation & Resilience Coach for MCATai, the second of the 7 planned MCAT agents. MIRA is triggered when ARIA (or, later, any other MCAT agent) sets `suggested_handoff == 'mira'` due to detected student frustration. Unlike ARIA, MIRA is explicitly not a content tutor — its job is emotional support, effort validation, and knowing its own limits (escalating to a human rather than attempting therapy).

### Background

> Why is this change needed? What problem does it solve?

ARIA (see `changes/2026/07/10/aria-agent/`) already sets `suggested_handoff = 'mira'` when its frustration heuristic crosses a threshold, but no agent exists yet to receive that handoff. Without MIRA, a frustrated student has nowhere to go — ARIA would just keep tutoring past the point where tutoring is the wrong intervention. MIRA closes that loop and is the natural second agent to build, since it's the only handoff target ARIA currently references.

### Current State

> What exists today? What are the limitations?

- `apps/backend` scaffold, Pydantic contract mirrors (`AgentInput`/`AgentOutput`), the Python `BaseAgent` ABC, and `PromptRegistryClient`/`FilePromptRegistryClient` all exist and are stable (`changes/2026/07/10/aria-agent/`).
- ARIA exists and sets `suggested_handoff = 'mira'` but nothing consumes that signal.
- No mechanism exists for a receiving agent to learn *why* it was handed off to — `AgentInput` has no dedicated "prior agent context" field.

---

## User Stories

- As a frustrated student, I want to be met with empathy and validation rather than more explanation, so that I don't feel like a failure for struggling.
- As a student who's overwhelmed, I want a concrete, low-effort next step (take a break, switch topics, try an easier angle), so that I have somewhere to go besides "keep pushing."
- As a student whose mood has genuinely improved, I want to be handed back to ARIA rather than kept in a coaching loop I no longer need.
- As the platform, I want MIRA to recognize the edge of its competence and escalate to a human rather than attempt therapy, so that no student in real distress is left with only an AI's response.

## Functional Requirements

### FR1: MIRA Identity & Core Behavior

**Description:** Implement `apps/backend/domains/mcat/agents/mira.py`, extending the Python `BaseAgent` (same class ARIA extends).

**Behavior:**
- `respond()` shall acknowledge the specific struggle before offering anything else (e.g. naming the concept/topic that triggered the handoff, not a generic "I'm sorry you're struggling").
- `respond()` shall validate the student's effort, not just outcomes.
- `respond()` shall offer exactly one concrete strategy per turn (e.g. take a break, switch topics, try a simpler angle) — not a list of options, which can itself feel overwhelming.
- `respond()` shall frame encouragement in growth-mindset terms (effort and strategy change outcomes, not fixed ability).
- `fetch_prompt()` shall retrieve MIRA's system prompt via the existing `PromptRegistryClient` abstraction (no new client code needed — see FR5).

**Constraints:**
- MIRA is explicitly not a tutor — `respond()` must not introduce or continue MCAT content instruction. That's ARIA's job (see FR2 for handing back).

### FR2: Context Access (Why Was MIRA Triggered?)

**Description:** MIRA needs to know what caused the handoff — specifically, the frustration context ARIA recorded.

**Behavior:**
- MIRA shall read the most recent `EpisodicMemory` entry in `AgentInput.episodic_context` for context about the triggering struggle (the same channel ARIA already uses for its own `consecutive_successful_turns` marker — see `changes/2026/07/10/aria-agent/`). No new `AgentInput` field is introduced.
- If no relevant prior context is found (e.g. MIRA invoked directly without a prior ARIA turn), MIRA shall acknowledge the struggle generically from `AgentInput.message` rather than fail.

**Constraints:**
- This reuses an existing, already-approved channel rather than adding a new field to the immutable `AgentInput`/`AgentOutput` contract. If a real "handoff context" mechanism is designed later (e.g. as part of the paused `core-data-schema` epic), this should be revisited (see Open Questions).

### FR3: Handoff Rules

**Description:** MIRA shall set `AgentOutput.suggested_handoff` and `risk_level` based on the student's emotional trajectory.

**Behavior:**
- If positive/recovery signals are detected in the last 2 messages, `suggested_handoff` shall be `'aria'` (return to tutoring).
- If a distress estimate exceeds `0.85`, `risk_level` shall be `'high'` (signal for human escalation via `DomainConfig.escalationRules`, not a domain-agent handoff).
- `suggested_handoff` shall never be `'quinn'` — a frustrated/distressed student does not get routed to practice questions, regardless of any other signal.
- If neither recovery nor high distress is detected, `suggested_handoff` shall be `null` (MIRA continues coaching).
- Recovery-signal and distress-level detection use interim heuristics (keyword/pattern-based), exposed behind swappable protocols (`RecoverySignalClassifier`, `DistressEstimator`), matching the pattern established for ARIA's `FrustrationEstimator`/`TurnOutcomeClassifier` (see `changes/2026/07/10/aria-agent/SPEC.md` FR4).

**Constraints:**
- Distress/recovery detection must be deterministic and unit-testable, same constraint as ARIA's FR4.

### FR4: Prohibited Behaviors / Safety Guardrails

**Description:** MIRA shall never exhibit specific behaviors, regardless of prompt content.

**Behavior:**
- MIRA shall never provide therapy or mental health diagnosis.
- MIRA shall never minimize the student's feelings (e.g. phrases like "it's not that hard").
- MIRA shall never push MCAT content when the student is emotionally overwhelmed (ties to FR1's "not a tutor" constraint).
- MIRA shall never promise a specific emotional outcome (e.g. "you'll feel better if...").

**Constraints:**
- The distress-escalation check (FR3) runs independently of prompt content, same reasoning as ARIA's medical-advice guard (first-layer guard, not the only one — full jailbreak-resistance out of scope).

### FR5: Prompt Fetching

**Description:** MIRA's system prompt, fetched via the existing `PromptRegistryClient` abstraction.

**Behavior:**
- `domains/mcat/prompts/mira_v1.md` shall contain MIRA's full system prompt (identity, empathy-first method, growth-mindset framing, prohibited behaviors) — authored content.
- No new `PromptRegistryClient`/`FilePromptRegistryClient` code — MIRA reuses what ARIA already built (`apps/backend/prompt_registry/client.py`), just with `agent_id='mira'`.

## Non-Functional Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| Handoff logic determinism | Same `session_history`/`episodic_context` input always yields same `suggested_handoff`/`risk_level` | Unit tests |
| Test coverage | All FR1–FR4 behaviors have at least one passing test | pytest suite |
| No regression | ARIA's existing 13 tests still pass unchanged | pytest suite (full run) |

## Technical Design

### Architecture

```
apps/backend/domains/mcat/agents/
├── aria.py                          # existing
└── mira.py                          # NEW — this change

domains/mcat/prompts/
├── aria_v1.md                       # existing
└── mira_v1.md                       # NEW — this change
```

MIRA extends the same `apps/backend/domains/_contracts/base_agent.py::BaseAgent` ARIA extends — no changes to `_contracts/`.

### Data Model

> No database schema changes — same as the ARIA change, the persistence layer doesn't exist yet (paused `core-data-schema` epic).

### Algorithms / Business Logic

**Reading the handoff cause (FR2):** Sort `episodic_context` by `occurredAt` descending, take the most recent entry's `summary` as the frustration context. If `episodic_context` is empty, fall back to acknowledging `message` directly.

**Distress estimate (interim heuristic):** Similar shape to ARIA's `KeywordFrustrationEstimator` but scores a distinct, higher-severity marker set (e.g. explicit hopelessness/self-deprecation language) over the recent user messages, on a 0–1 scale.

**Recovery-signal detection (interim heuristic):** Scans the last 2 user messages for positive-affect markers (e.g. "feeling better," "okay let's try again," "thanks, that helps").

**Edge Cases:**
- `episodic_context` empty and `session_history` empty (MIRA invoked as the very first turn, no prior ARIA context): acknowledge `message` generically, no recovery/distress signal assumed, `suggested_handoff = null`.
- Distress > 0.85 **and** recovery signals present simultaneously (contradictory turn): distress escalation takes priority — `risk_level = 'high'` wins over the recovery handoff, since safety supersedes a "feels better" surface signal that could itself be masking distress.

## API Contract

> N/A — no new HTTP endpoints. Same as the ARIA change (`GET /health` remains the only endpoint).

## Security Considerations

- **Data Protection:** No mental-health diagnosis content is generated or stored; `risk_level = 'high'` is the observability hook for downstream HITL escalation, consistent with ARIA's medical-advice guard.
- **Input Validation:** Same as ARIA — Pydantic validates `AgentInput` at the boundary.

## Error Handling

| Error Scenario | User Message | Log Level | Recovery |
|----------------|--------------|-----------|----------|
| `episodic_context` empty (no prior ARIA turn) | MIRA acknowledges `message` generically | INFO | No special handling — degrades gracefully |
| Distress > 0.85 | MIRA responds with acknowledgment + escalation framing | WARN | `risk_level = 'high'` set for downstream HITL review |

## Observability

### Logging

| Event | Level | Fields |
|-------|-------|--------|
| Handoff back to ARIA | INFO | agent_id, suggested_handoff |
| High-distress turn | WARN | agent_id, risk_level |

### Metrics

| Metric | Type | Labels |
|--------|------|--------|
| mira_handoff_total | counter | target_agent |
| mira_high_risk_total | counter | reason |

## Acceptance Criteria

- [ ] **AC1:** Given `episodic_context` contains a recent entry referencing a specific struggle, when MIRA responds, then the response acknowledges that specific struggle (not a generic acknowledgment).
- [ ] **AC2:** Given any MIRA response, when its content is inspected, then it validates effort and offers exactly one concrete strategy.
- [ ] **AC3:** Given positive/recovery signals in the last 2 user messages, when MIRA responds, then `AgentOutput.suggested_handoff == 'aria'`.
- [ ] **AC4:** Given a distress estimate above 0.85, when MIRA responds, then `AgentOutput.risk_level == 'high'`.
- [ ] **AC5:** Given any input, when MIRA responds, then `AgentOutput.suggested_handoff` is never `'quinn'`.
- [ ] **AC6:** Given distress > 0.85 and recovery signals simultaneously present, when MIRA responds, then `risk_level == 'high'` takes priority over the `'aria'` handoff.
- [ ] **AC7:** Given any MIRA response, when its content is inspected, then it never minimizes feelings, never pushes MCAT content, and never promises a specific emotional outcome.
- [ ] **AC8:** Given the full existing ARIA test suite, when it's re-run after this change, then all 13 tests still pass unchanged (no regression).

## Domain Model

### Entities

| Entity | Definition | Spec Path | Status |
|--------|------------|-----------|--------|
| MIRA | The Motivation & Resilience Coach; second of 7 planned MCAT agents | specs/domain/definitions/mira.md | New |

`specs/domain/glossary.md`'s "MCAT Domain Agents" table already lists MIRA ("Motivation Coach — detects frustration/burnout, provides encouragement") — this change is its first implementation, not a new glossary entry.

### Relationships

```text
ARIA ──suggested_handoff='mira'──► MIRA (triggered)
MIRA ──reads (via episodic_context)──► ARIA's prior session_notes (frustration cause)
MIRA ──suggested_handoff='aria'──► ARIA (recovery)
MIRA ──risk_level='high'──► human escalation (DomainConfig.escalationRules; not wired yet)
```

### Glossary

No new terms — `MIRA`, `Handoff`, `BaseAgent`, `AgentInput`, `AgentOutput` all pre-exist in `specs/domain/glossary.md`.

### Bounded Contexts

- **MCAT Agent Context**: ARIA, MIRA (this change); QUINN, SAGE, VERA, SCOUT, ATLAS referenced by id but not implemented.

## Specs Directory Changes

### Before

```text
specs/domain/definitions/
├── base-agent.md
├── domain-config.md
├── domain-registry.md
└── aria.md
```

### After

```text
specs/domain/definitions/
├── base-agent.md
├── domain-config.md
├── domain-registry.md
├── aria.md
└── mira.md              # NEW
```

### Changes Summary

| Path | Action | Description |
|------|--------|--------------|
| specs/domain/definitions/mira.md | Create | MIRA's identity, behavior rules, handoff thresholds, prohibited behaviors |

## Components

> Same gap as the ARIA change — no SDD component type for Python/FastAPI code in the active tech pack. This change adds to the existing untracked `apps/backend`.

## System Analysis

### Inferred Requirements

- A real "handoff context" contract field (rather than piggybacking on `episodic_context`) may be worth formalizing once a third agent needs similar cross-agent context — tracked as an Open Question.

### Gaps & Assumptions

- Assumes `AgentInput.episodic_context`, sorted by `occurredAt`, is a reasonable-enough proxy for "what did the previous agent just say" until real persistence/handoff-context exists.
- Assumes "distress" and "recovery" are approximated by interim heuristics, not a production ML/sentiment model — same assumption class as ARIA's FR4.

### Cross-References

- `changes/2026/07/10/aria-agent/` — MIRA's handoff trigger, the `BaseAgent`/contract mirrors it reuses, and the heuristic-placeholder pattern it follows.
- `specs/domain/glossary.md` — pre-existing MIRA, Handoff entries.

## Requirements Discovery

### Questions & Answers

| Step | Question | Answer |
|------|----------|--------|
| Scope | How does MIRA learn why it was handed off, given no dedicated contract field exists? | Reuse `episodic_context`, the same channel ARIA already uses for its own cross-turn signal — no new `AgentInput` field. |

### User Feedback

- User specified MIRA's identity, handoff rules, and prohibited behaviors in full detail up front; no scope pushback during proposal.

## Domain Updates

### Glossary Terms

No changes — MIRA is a pre-existing glossary entry.

### Definition Specs

| File | Description | Action |
|------|-------------|--------|
| `mira.md` | MIRA's full identity, behavior rules, handoff thresholds, prohibited behaviors | create |

## Testing Strategy

### Unit Tests

| Component | Test Case | Expected Behavior |
|-----------|-----------|--------------------|
| mira.py | Respond with `episodic_context` referencing a specific struggle | Acknowledges that specific struggle (AC1) |
| mira.py | Respond to any input | Validates effort, offers exactly one strategy (AC2) |
| mira.py | Last 2 user messages show recovery signals | `suggested_handoff == 'aria'` (AC3) |
| mira.py | Distress estimate > 0.85 | `risk_level == 'high'` (AC4) |
| mira.py | Any input | `suggested_handoff` never `'quinn'` (AC5) |
| mira.py | Distress > 0.85 AND recovery signals present | `risk_level == 'high'` wins (AC6) |
| mira.py | Any response | No minimizing language, no MCAT content, no outcome promises (AC7) |
| (full suite) | Re-run all existing ARIA tests | 13/13 still pass (AC8) |

### Integration/E2E Tests

N/A — same as the ARIA change (no NEXUS/SSE wiring yet).

### Test Data

| Entity | Required State | Purpose |
|--------|-----------------|---------|
| Fixture `episodic_context` (ARIA's frustration-cause summary) | Contains a specific struggle reference | AC1 |
| Fixture `session_history` (2 recovery-signal messages) | Positive-affect markers present | AC3 |
| Fixture `session_history` (distress markers) | High-severity distress language | AC4, AC6 |

## Dependencies

### Internal Dependencies

| Component | Version | Reason |
|-----------|---------|--------|
| `changes/2026/07/10/aria-agent/` | Complete | `BaseAgent`, contract mirrors, `PromptRegistryClient` all reused as-is |

## Migration / Rollback

Nothing depends on MIRA yet (not served over HTTP) — revert the commit/PR to roll back.

## Out of Scope

- A dedicated "handoff context" contract field — FR2 reuses `episodic_context` instead; revisit if a third agent needs the same thing (see Open Questions).
- NEXUS/LangGraph/SSE wiring — same as ARIA, none of this exists yet.
- Real distress/recovery ML models — FR3 uses interim heuristics, same pattern as ARIA's FR4.
- Actual human-escalation wiring for `risk_level = 'high'` — this change only sets the field; nothing consumes it yet (same as ARIA's medical-advice guard).
- The remaining 5 MCAT agents (QUINN, SAGE, VERA, SCOUT, ATLAS).

## Open Questions

- [ ] Should a dedicated "handoff context" field be added to `AgentInput` once a third agent needs similar cross-agent context, rather than continuing to piggyback on `episodic_context`?
- [ ] Same open question as the ARIA change: when should real distress/recovery signal models replace these heuristics?

## References

- `changes/2026/07/10/aria-agent/` — BaseAgent, contract mirrors, PromptRegistryClient, heuristic-placeholder pattern
- `specs/domain/glossary.md` — pre-existing MIRA, Handoff entries
- `specs/architecture/overview.md` — HITL Escalation Bus (L2), referenced for future risk_level wiring
