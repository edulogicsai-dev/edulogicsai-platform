---
title: MIRA — Motivation & Resilience Coach (MCAT)
type: feature
status: active
domain: mcat
issue: TBD
created: 2026-07-15
updated: 2026-07-22
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
- If positive/recovery signals are detected, `suggested_handoff` shall be `'aria'` (return to tutoring).
- If distress is severe enough to warrant human escalation, `risk_level` shall be `'high'` (signal for human escalation via `DomainConfig.escalationRules`, not a domain-agent handoff).
- `suggested_handoff` shall never be `'quinn'` — a frustrated/distressed student does not get routed to practice questions, regardless of any other signal.
- If neither recovery nor high distress is detected, `suggested_handoff` shall be `null` (MIRA continues coaching).

**Amended 2026-07-22 — LLM judgment, not keyword heuristics:** as originally drafted here, both recovery and distress-severity detection were keyword heuristics behind swappable protocols (`RecoverySignalClassifier`, `DistressEstimator`), mirroring ARIA's original `FrustrationEstimator`/`TurnOutcomeClassifier` split. Since MIRA's entire purpose is reading emotional state — unlike ARIA, where only frustration (not the readiness/streak signal) moved to the LLM — *both* signals moved together here: `mira.py` now calls Claude Sonnet (via `LiteLLMGatewayClient`, model alias `sonnet-tutor`) and both `recovered` (boolean) and `risk_level` (`"low" | "medium" | "high"`) come back as fields in the same structured JSON completion that produces MIRA's coaching `response` text. `RecoverySignalClassifier`/`DistressEstimator`/`KeywordDistressEstimator`/`KeywordRecoverySignalClassifier` were all removed — no keyword list remains in `mira.py`.
- Distress-takes-priority-over-recovery (FR3's edge case, and AC6) is still enforced deterministically in Python: if the model reports `risk_level: "high"`, `mira.py` forces `suggested_handoff = null` regardless of what the model's own `recovered` field says, rather than trusting the model to never report both.
- **Resolved 2026-07-22 (see FR4's "Resolved" amendment for the full account):** `risk_level` is no longer purely the model's judgment as stated above — a deterministic keyword guard can also force it to `'high'` independently, as a safety floor under the model's own detection, not instead of it.

**Constraints:**
- Distress/recovery detection is no longer independently unit-testable without a mocked LLM response — tests inject a fake `LiteLLMGatewayClient` returning canned `recovered`/`risk_level` values (see `tests/test_mira.py`), the same pattern as ARIA's amended FR4 and `nexus/intent_classifier.py`'s `LiteLLMIntentClassifier`. The distress-wins-over-recovery priority rule itself remains deterministic and unit-testable (it's a plain Python `if`, not a model judgment).

### FR4: Prohibited Behaviors / Safety Guardrails

**Description:** MIRA shall never exhibit specific behaviors, regardless of prompt content.

**Behavior:**
- MIRA shall never provide therapy or mental health diagnosis.
- MIRA shall never minimize the student's feelings (e.g. phrases like "it's not that hard").
- MIRA shall never push MCAT content when the student is emotionally overwhelmed (ties to FR1's "not a tutor" constraint).
- MIRA shall never promise a specific emotional outcome (e.g. "you'll feel better if...").

**Constraints:**
- The distress-escalation check (FR3) originally ran independently of prompt content, same reasoning as ARIA's medical-advice guard (first-layer guard, not the only one — full jailbreak-resistance out of scope).

**Amended 2026-07-22 — correction, not just a rewording:** unlike ARIA's medical-advice guard (which stayed a pre-LLM, deterministic regex check even after ARIA's own LLM wiring — see `aria-agent/SPEC.md` FR5's amendment), MIRA's distress-escalation signal is *not* independent of the LLM call — `risk_level` is now the model's own judgment (FR3 amendment), not a separate keyword guard running alongside it. This is a real behavioral difference between the two agents' safety boundaries, not just a documentation gap: MIRA has no equivalent of ARIA's deterministic medical-advice guard, because MIRA's whole job (reading distress) is exactly the judgment that was moved to the LLM. What *is* still deterministic here is the distress-wins-over-recovery priority rule (see FR3 amendment) — that's the actual safety-relevant guarantee this constraint should be understood as protecting now.

**Resolved 2026-07-22 (same day, follow-up):** `mira.py` now has a deterministic distress guard, matching ARIA's medical-advice guard structurally (a pre-LLM, regex-based check against `input.message`, applied independently of the LLM call). `_is_high_distress_message()` checks for high-severity distress language in three conservative, high-precision categories: explicit self-harm language (`"kill myself"`, `"end my life"`/`"ending my life"`, `"end it all"`/`"ending it all"`, `"suicide"`/`"suicidal"`, `"self-harm"`, `"hurt myself"`, `"want to die"`, `"don't want to be alive/live/exist"`), hopelessness (`"give up on everything"`, `"no point"`, `"can't do this anymore"`), and self-worth (`"I'm worthless"`, `"I'm a failure"`). When matched, `respond()` forces `risk_level = 'high'` regardless of what the model's own JSON completion reports — the same override relationship ARIA's medical guard has to ARIA's `risk_level`.
- **This is a floor, not a replacement for FR3's model-driven detection.** The guard only ever raises `risk_level` to `'high'`; it never lowers it, and it does not suppress or replace the model's own judgment — a message with none of these exact phrases can still reach `risk_level = 'high'` via the model reading subtler distress signals (unchanged from FR3's amendment; see `tests/test_mira.py`'s `test_model_can_still_independently_report_high_risk_guard_misses`).
- Interacts with the distress-wins-over-recovery rule (FR3) exactly as the model-driven path does: a guard-triggered `'high'` also forces `suggested_handoff = null`, even if the model's `recovered` field said `true` (`tests/test_mira.py`'s `test_distress_guard_also_suppresses_a_simultaneous_recovery_report`).
- Deliberately narrow phrases (not single words like "worthless" or "failure" alone) — false negatives here are acceptable (the model is still the primary detector for anything the guard misses); false positives on a legitimately low-risk turn are not, since they'd trigger unnecessary human escalation.

### FR5: Prompt Fetching

**Description:** MIRA's system prompt, fetched via the existing `PromptRegistryClient` abstraction.

**Behavior:**
- `domains/mcat/prompts/mira_v1.md` shall contain MIRA's full system prompt (identity, empathy-first method, growth-mindset framing, prohibited behaviors) — authored content.
- No new `PromptRegistryClient`/`FilePromptRegistryClient` code — MIRA reuses what ARIA already built (`apps/backend/prompt_registry/client.py`), just with `agent_id='mira'`.

## Non-Functional Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| Handoff logic determinism | Same `session_history`/`episodic_context` input always yields same `suggested_handoff`/`risk_level` — **amended 2026-07-22: no longer true in the strict sense — both signals now depend on a live model's judgment (FR3 amendment); the priority rule (distress wins over recovery) is what's still guaranteed deterministic** | Mocked-LLM tests |
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

**Distress and recovery detection (amended 2026-07-22):** originally two separate keyword-heuristic scans (kept in git history) — one over a higher-severity marker set (hopelessness/self-deprecation language) for distress, one over positive-affect markers for recovery. Both are now a single LLM call: `mira.py` sends `mira_v1.md`'s content plus an appended JSON-format instruction to `sonnet-tutor`, and parses `recovered`/`risk_level` from the response (see LLM Response Contract below).

**Edge Cases:**
- `episodic_context` empty and `session_history` empty (MIRA invoked as the very first turn, no prior ARIA context): acknowledge `message` generically, no recovery/distress signal assumed, `suggested_handoff = null`.
- Distress and recovery signals present simultaneously (contradictory turn) — i.e. the model reports both `risk_level: "high"` and `recovered: true`: distress escalation takes priority, enforced in Python (FR3 amendment) — `risk_level = 'high'` wins over the recovery handoff, since safety supersedes a "feels better" surface signal that could itself be masking distress.

### LLM Response Contract (Added 2026-07-22)

`respond()`'s system prompt is `domains/mcat/prompts/mira_v1.md`'s content (FR5) plus an appended, code-owned JSON-format instruction requiring the model to return exactly:

```json
{
  "response": "<coaching message>",
  "recovered": true,
  "risk_level": "low",
  "session_notes": "<brief internal note: emotional state observed, strategy offered, whether you see improvement>"
}
```

Unlike ARIA, MIRA's `session_notes` is the model's own text (not a Python-encoded marker) — nothing downstream regex-parses it the way ARIA's `consecutive_successful_turns` marker is parsed back out of `episodic_context`. A non-JSON or malformed completion raises `LLMResponseParseError`, left to propagate the same way as ARIA (see that spec's amendment) — `sse-endpoint`'s existing SSE error handling turns it into a graceful `event: error`.

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
- [ ] **AC3:** Given the model's structured response reports `recovered: true` (amended 2026-07-22 — originally "positive/recovery signals in the last 2 user messages"), when MIRA responds, then `AgentOutput.suggested_handoff == 'aria'`.
- [ ] **AC4:** Given the model's structured response reports `risk_level: "high"` (amended 2026-07-22 — originally "a distress estimate above 0.85"), when MIRA responds, then `AgentOutput.risk_level == 'high'`.
- [ ] **AC5:** Given any input, when MIRA responds, then `AgentOutput.suggested_handoff` is never `'quinn'`.
- [ ] **AC6:** Given the model's structured response reports both `risk_level: "high"` and `recovered: true` simultaneously (amended 2026-07-22 — originally "distress > 0.85 and recovery signals simultaneously present"), when MIRA responds, then `risk_level == 'high'` takes priority over the `'aria'` handoff — this priority check itself stays a deterministic Python `if`, not a model judgment.
- [ ] **AC7:** Given any MIRA response, when its content is inspected, then it never minimizes feelings, never pushes MCAT content, and never promises a specific emotional outcome.
- [ ] **AC8:** Given the full existing ARIA test suite, when it's re-run after this change, then all 13 tests still pass unchanged (no regression).
- [ ] **AC9 (Added 2026-07-22):** Given `input.message` contains a high-severity distress keyword (explicit self-harm language, "give up on everything"/"no point"/"can't do this anymore", "I'm worthless"/"I'm a failure"), when MIRA responds — even if the model's own structured response reports `risk_level: "low"` — then `AgentOutput.risk_level == 'high'`, and if the model also reported `recovered: true`, `suggested_handoff` is still `null` (same priority as AC6).
- [ ] **AC10 (Added 2026-07-22):** Given `input.message` contains none of AC9's guard keywords, when the model's own structured response independently reports `risk_level: "high"`, then `AgentOutput.risk_level == 'high'` — the guard must not suppress or interfere with the model's own detection of subtler signals.

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
- Assumes "distress" and "recovery" are approximated by interim heuristics, not a production ML/sentiment model — same assumption class as ARIA's FR4. **Amended 2026-07-22:** no longer true — both now come from the LLM's own judgment (FR3 amendment), not a heuristic, though still not a dedicated SentimentTool service (same caveat as ARIA's equivalent amendment).

### Cross-References

- `changes/2026/07/10/aria-agent/` — MIRA's handoff trigger, the `BaseAgent`/contract mirrors it reuses, and (as of 2026-07-22) the real-LLM-wiring pattern (`LiteLLMGatewayClient`, `llm_support.py`'s shared JSON-completion plumbing) it also follows.
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
| mira.py | Mocked `LiteLLMGatewayClient` returns `recovered: true` (amended 2026-07-22; was "last 2 user messages show recovery signals") | `suggested_handoff == 'aria'` (AC3) |
| mira.py | Mocked `LiteLLMGatewayClient` returns `risk_level: "high"` (amended 2026-07-22; was "distress estimate > 0.85") | `risk_level == 'high'` (AC4) |
| mira.py | Any input | `suggested_handoff` never `'quinn'` (AC5) |
| mira.py | Mocked response reports `risk_level: "high"` AND `recovered: true` (amended 2026-07-22) | `risk_level == 'high'` wins (AC6) |
| mira.py | Any response | No minimizing language, no MCAT content, no outcome promises (AC7) |
| mira.py | `message` matches a guard keyword; mocked response reports `risk_level: "low"` (Added 2026-07-22) | Guard overrides — `risk_level == 'high'` (AC9) |
| mira.py | `message` matches a guard keyword; mocked response reports `risk_level: "low"`, `recovered: true` (Added 2026-07-22) | `risk_level == 'high'`, `suggested_handoff is None` (AC9) |
| mira.py | `message` matches no guard keyword; mocked response independently reports `risk_level: "high"` (Added 2026-07-22) | Guard doesn't suppress the model's own detection — `risk_level == 'high'` (AC10) |
| mira.py | `message` matches no guard keyword, ordinary frustration only (Added 2026-07-22) | Guard doesn't false-positive — `risk_level == 'low'` |
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
- ~~Real distress/recovery ML models~~ — partially done 2026-07-22: both now come from the LLM's own judgment (FR3 amendment), not a keyword heuristic, though still not a dedicated ML/sentiment service.
- Actual human-escalation wiring for `risk_level = 'high'` — this change only sets the field; nothing consumes it yet (same as ARIA's medical-advice guard).
- The remaining 5 MCAT agents (QUINN, SAGE, VERA, SCOUT, ATLAS).

## Open Questions

- [ ] Should a dedicated "handoff context" field be added to `AgentInput` once a third agent needs similar cross-agent context, rather than continuing to piggyback on `episodic_context`?
- [x] Same open question as the ARIA change: when should real distress/recovery signal models replace these heuristics? **Resolved 2026-07-22:** both moved to the LLM's own judgment together (unlike ARIA, which split — see `aria-agent/SPEC.md` FR4 amendment for why MIRA's case differs: MIRA's whole purpose is reading emotional state, so there's no equivalent "deterministic streak counter" piece to keep separate).

## References

- `changes/2026/07/10/aria-agent/` — BaseAgent, contract mirrors, PromptRegistryClient, heuristic-placeholder pattern
- `specs/domain/glossary.md` — pre-existing MIRA, Handoff entries
- `specs/architecture/overview.md` — HITL Escalation Bus (L2), referenced for future risk_level wiring
