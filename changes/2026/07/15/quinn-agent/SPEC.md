---
title: QUINN — Practice Question Intelligence Agent (MCAT)
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

Implement QUINN — the Practice Question Intelligence agent for MCATai, the third of the 7 planned MCAT agents. QUINN is triggered when ARIA sets `suggested_handoff == 'quinn'` (student ready for practice) and, later, when it hands a student back to itself after a completed question. Unlike ARIA and MIRA, QUINN requires genuine multi-turn state: present a question, wait for the student's answer, then explain — never the reverse.

### Background

> Why is this change needed? What problem does it solve?

ARIA (`changes/2026/07/10/aria-agent/`) already sets `suggested_handoff = 'quinn'` after 4+ consecutive successful turns, but nothing receives that handoff. QUINN closes that loop and exercises a capability neither ARIA nor MIRA needed: holding state across a question/answer pair with no persistence layer available yet.

### Current State

> What exists today? What are the limitations?

- `apps/backend` scaffold, Pydantic contract mirrors, `BaseAgent`, `PromptRegistryClient` all exist and are stable (`changes/2026/07/10/aria-agent/`).
- ARIA and MIRA both exist; ARIA sets `suggested_handoff = 'quinn'` but nothing consumes it. MIRA established the pattern of encoding cross-turn state into `session_notes`/`episodic_context` in the absence of real persistence (`changes/2026/07/15/mira-agent/`) — QUINN extends that same pattern to a genuinely stateful question/answer cycle.
- No LLM integration (LiteLLM) exists yet — question *content* generation in this change is a deterministic templated placeholder, not real MCAT-quality item writing.

---

## User Stories

- As a student who's shown readiness, I want a practice question at the right difficulty for what I just learned, so I can test myself rather than keep receiving explanations.
- As a student, I want to attempt the question myself before seeing any explanation, so the practice actually tests my understanding.
- As a student who got it wrong, I want to understand not just the right answer but *why each wrong option is wrong*, so I learn from the mistake instead of just being corrected.
- As a student who keeps missing questions on the same concept, I want to be sent back to ARIA for re-teaching rather than given more questions I'm not ready for.
- As a student doing well, I want to be routed toward an updated study plan (SCOUT) once I've demonstrated solid practice performance.

## Functional Requirements

### FR1: Question/Answer State Machine

**Description:** QUINN must track, across turns, whether there's a pending unanswered question for this session — with no persistence layer available yet.

**Behavior:**
- QUINN shall encode pending-question state (concept key, correct answer, distractor explanations, cited chunk ids, streak counters) into `AgentOutput.session_notes` as a single structured marker string, mirroring the pattern MIRA/ARIA already use for cross-turn signals (see `changes/2026/07/15/mira-agent/SPEC.md` FR2, `changes/2026/07/10/aria-agent/SPEC.md` FR4).
- On each turn, QUINN shall look for a pending-question marker in the most recent `episodic_context` entry (by `occurredAt`).
  - **No pending question found:** treat this as a fresh trigger — generate a new question (FR2) and present it. Do not evaluate `message` as an answer.
  - **Pending question found:** treat `AgentInput.message` as the student's attempt at that question. Evaluate it (FR3), respond with confirmation + distractor analysis, update streak counters, then apply handoff rules (FR4) before deciding whether to present another question.

**Constraints:**
- This reuses the existing `episodic_context`/`session_notes` channel rather than adding a new `AgentInput`/`AgentOutput` field (same constraint MIRA operated under — see Open Questions on formalizing this later).

### FR2: Question Generation (Amended 2026-07-22 — Real LLM, Not a Templated Placeholder)

**Description:** Generate one practice question at a time, grounded in `retrieved_chunks`.

**Behavior:**
- QUINN shall present exactly one question per turn — never a batch.
- The question shall be constructed from `retrieved_chunks` content (the concept ARIA handed off on, read via `episodic_context` per FR1).
- `AgentOutput.cited_chunks` shall reference the `ContentChunk.id`s the question was actually constructed from.
- Question difficulty shall not exceed the student's mastery tier + 1 (approximated the same way ARIA approximates mastery — via prior `episodic_context` mention counts for the concept, since `StudentProfile` has no per-concept mastery field; see `changes/2026/07/10/aria-agent/SPEC.md` FR3's equivalent discovery).
- The answer shall never be revealed in the same turn the question is presented.

**Amended 2026-07-22:** as originally drafted here (title kept for history, now inaccurate), the question was built from a deterministic template — no LLM call. `quinn.py` now calls Claude Sonnet (`LiteLLMGatewayClient`, model alias `sonnet-tutor`) via a new `LLMQuestionGenerator`, which replaced `TemplatedQuestionGenerator` entirely (removed, not kept as a fallback — every question, including in tests, now goes through the same `QuestionGenerator` interface backed by either a real or mocked LLM call). `cited_chunks` from the model's response is still filtered against `retrieved_chunks`' actual ids before reaching `AgentOutput` (`llm_support.py`'s `valid_cited_chunks`), same defensive pattern as ARIA.

**Constraints:**
- Question-generation quality is no longer an explicitly out-of-scope placeholder concern (see Out of Scope) — real question wording/answer/distractor content now comes from the model, via a `QuestionGenerator` protocol (kept as the DI seam) backed by `LLMQuestionGenerator`.

### FR3: Answer Evaluation & Distractor Analysis

**Description:** When a pending question exists, evaluate the student's answer and always explain fully.

**Behavior:**
- QUINN shall confirm whether the student's answer was correct or incorrect.
- QUINN shall explain why the correct answer is right, **and** why each incorrect option is wrong (distractor analysis) — every time, regardless of whether the student got it right.
- QUINN shall never skip distractor analysis.
- QUINN shall update `consecutive_correct`, `consecutive_wrong`, `questions_completed`, and `correct_count` counters (encoded via FR1's session_notes marker) after every evaluated answer.

**Amended 2026-07-22 — hybrid, correctness stays deterministic:** correctness itself (was the student's answer right or wrong) is **not** an LLM judgment — `quinn.py` still does an exact, case-insensitive string comparison against the stored `correct_answer` from the pending-question marker, unchanged from the original design. What moved to the LLM is the *explanation text* (the actual distractor-analysis prose) and, in the same call, frustration detection (see FR4 amendment) — both come back as fields (`explanation`, `frustration_detected`) in a structured JSON completion. Correctness grading a known answer doesn't benefit from a model's judgment, and the streak/ease-factor math downstream needs it to be exactly reproducible turn to turn — that's why it stayed deterministic even though question generation (FR2) and explanation prose did not.

**Constraints:**
- Distractor *content* (the correct/incorrect answer text and reasons) is generated once, at question-presentation time (FR2), and stored in the pending-question marker — the evaluation call (this FR) writes fresh explanation *prose* around those stored facts, it doesn't regenerate or second-guess them.

### FR4: Handoff Rules

**Description:** QUINN shall set `AgentOutput.suggested_handoff` and `risk_level` based on question performance and frustration signals.

**Behavior:**
- If the student gets 3+ consecutive wrong answers on the same concept, `suggested_handoff` shall be `'aria'` (needs re-teaching, not more questions).
- If the student completes 5+ questions with 80%+ overall accuracy, `suggested_handoff` shall be `'scout'` (ready for a study plan update).
- If frustration is detected, `suggested_handoff` shall be `'mira'`.
- If multiple conditions are met simultaneously, priority order is: frustration (`'mira'`) > consecutive-wrong (`'aria'`) > accuracy milestone (`'scout'`) — a distressed student takes priority over a purely academic handoff, and needing re-teaching takes priority over being routed to a study-plan update.
- If none of the above, `suggested_handoff` shall be `null` and QUINN presents another question.

**Amended 2026-07-22:** frustration was originally a keyword-heuristic estimate over the last 3 messages (same shape as ARIA's original `KeywordFrustrationEstimator`, which QUINN imported and reused directly). It's now the `frustration_detected` boolean returned by the same evaluation-phase LLM call described in FR3's amendment — QUINN no longer imports anything frustration-related from `aria.py` (that import was removed along with `KeywordFrustrationEstimator` itself, which no longer exists in either file). Consecutive-wrong and accuracy-milestone detection are unchanged — both are exact counter arithmetic over deterministic state (FR1/FR3), not judgment calls, so neither moved to the LLM.

**Constraints:**
- Consecutive-wrong and accuracy-milestone detection remain deterministic and unit-testable with no live LLM call. Frustration detection requires a mocked LLM response in tests, same as ARIA/MIRA's amended FR4/FR3 — the priority order itself (frustration > consecutive-wrong > accuracy) is a plain Python `if`/`elif` chain and stays fully deterministic regardless of how frustration is sourced.

### FR5: Prohibited Behaviors / Safety Guardrails

**Description:** QUINN shall never exhibit specific behaviors, regardless of prompt content.

**Behavior:**
- QUINN shall never reveal the answer before the student has attempted the question.
- QUINN shall never skip distractor analysis after an answer is given.
- QUINN shall never present a question above the student's mastery tier + 1 (FR2).
- QUINN shall never provide medical advice or diagnosis — same guard as ARIA (`changes/2026/07/10/aria-agent/SPEC.md` FR5), applied independently of prompt content.

**Confirmed unchanged 2026-07-22:** like ARIA's medical-advice guard (and unlike MIRA's distress check, which moved to the LLM — see `mira-agent/SPEC.md` FR4's amendment), QUINN's medical-advice guard is still a plain Python regex check against `message`, evaluated *before* any LLM call — when it fires, `quinn.py` returns immediately with a deterministic decline message and `risk_level = 'high'`, preserving any pending question unchanged (FR1), without ever calling `sonnet-tutor` for that turn.

## Non-Functional Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| State-machine determinism | Same `episodic_context`/`message` input always yields the same evaluation/handoff | **Amended 2026-07-22: true for correctness grading, streak/ease-factor counters, and the consecutive-wrong/accuracy handoff branches — question wording, distractor explanation prose, and frustration-driven handoff now depend on a live model (FR2/FR3/FR4 amendments)** — Unit tests (deterministic paths); mocked-LLM tests (question/explanation/frustration) |
| Test coverage | All FR1–FR5 behaviors have at least one passing test | pytest suite |
| No regression | ARIA's and MIRA's existing 21 tests still pass unchanged | pytest suite (full run) |

## Technical Design

### Architecture

```
apps/backend/domains/mcat/agents/
├── aria.py                          # existing
├── mira.py                          # existing
└── quinn.py                         # NEW — this change

domains/mcat/prompts/
├── aria_v1.md                       # existing
├── mira_v1.md                       # existing
└── quinn_v1.md                      # NEW — this change
```

QUINN extends the same `BaseAgent` ARIA and MIRA extend — no changes to `_contracts/`.

### Data Model

> No database schema changes — same as prior MCAT agent changes (paused `core-data-schema` epic covers real persistence).

### Algorithms / Business Logic

**Pending-question marker format (session_notes):** `"quinn_pending: " + json.dumps({...})`, encoding concept, correct answer, distractor + reasons, and the four streak counters. **As implemented:** JSON rather than the ad-hoc key=value string originally sketched here, to avoid brittle parsing if chunk text or reasons contain `;`/`=` characters. Read back from the most recent `episodic_context` entry by `occurredAt`, same lookup pattern as ARIA/MIRA. When the medical-advice guard (FR5) fires while a question is pending, the same marker is re-emitted unchanged rather than lost.

**Question generation (amended 2026-07-22):** originally a deterministic template (kept in git history) producing a single true/false-style statement with one hardcoded distractor. Now: given a concept key (from `episodic_context`, per FR1) and `retrieved_chunks`, `LLMQuestionGenerator` sends `quinn_v1.md`'s content plus an appended JSON-format instruction to `sonnet-tutor` and parses `prompt_text`/`correct_answer`/`correct_reason`/`distractor`/`distractor_reason`/`cited_chunks` from the response (see LLM Response Contract below). The dataclass shape (`GeneratedQuestion`: one correct answer, one distractor, each with a reason) is unchanged from the original design — still a simplification relative to `quinn_v1.md`'s narrative description of full 4-option (A/B/C/D) MCQs with distractor analysis on every wrong option; real generation replaced the deterministic template, but the single-distractor structural simplification was kept rather than also expanding to 4 options, to keep this change scoped to "swap templates for real calls," not a redesign.

**Difficulty bound:** same heuristic as ARIA's mastery approximation — count of prior `episodic_context` mentions of the concept, capped so a concept mentioned 0 times only gets the most basic difficulty tier. Unchanged by the 2026-07-22 LLM wiring — still Python-computed, passed to the generator as an instruction ("never exceed one tier above the student's demonstrated level"), not something the model decides on its own.

**Edge Cases:**
- QUINN invoked with no `episodic_context` at all (no prior ARIA handoff, no pending question): fall back to generating a question grounded only in `retrieved_chunks`/`message`, difficulty tier 0.
- Student's `message` doesn't match either the correct answer or a recognized distractor (ambiguous/off-topic reply): treat as incorrect, still run full distractor analysis, don't crash or silently skip. Correctness comparison itself is still an exact string match (FR3 amendment) — unaffected by this edge case being ambiguous to a human reader, since the comparison is mechanical.
- All three handoff conditions technically met at once (frustration, 3+ wrong, 5+ questions at 80%+): frustration wins per FR4's stated priority order (extremely unlikely combination — 3+ consecutive wrong contradicts 80%+ overall accuracy in practice, but the priority order still resolves it deterministically, regardless of frustration now being LLM-sourced).

### LLM Response Contract (Added 2026-07-22)

Two distinct JSON contracts, appended to `quinn_v1.md`'s content depending on which phase `respond()` is in:

**Presenting a new question (FR2):**
```json
{
  "prompt_text": "<question, ending with 'Take your time -- what's your answer?'>",
  "correct_answer": "<exact expected reply>",
  "correct_reason": "<why it's correct>",
  "distractor": "<one plausible wrong answer>",
  "distractor_reason": "<why it's tempting but wrong>",
  "cited_chunks": ["<chunk_id>", "..."]
}
```

**Evaluating an answer (FR3/FR4):**
```json
{
  "explanation": "<full distractor-analysis prose, confirm correct/incorrect first>",
  "frustration_detected": true
}
```

Both go through `llm_support.py`'s shared `complete_json` (same helper ARIA/MIRA use). A non-JSON or malformed completion raises `LLMResponseParseError`, left to propagate the same way as ARIA/MIRA — `sse-endpoint`'s existing SSE error handling turns it into a graceful `event: error`.

## API Contract

> N/A — no new HTTP endpoints, same as ARIA/MIRA.

## Security Considerations

- **Data Protection:** Same medical-advice guard as ARIA; no new data-protection surface.
- **Input Validation:** Same as ARIA/MIRA — Pydantic validates `AgentInput` at the boundary.

## Error Handling

| Error Scenario | User Message | Log Level | Recovery |
|----------------|--------------|-----------|----------|
| No `retrieved_chunks` and no `episodic_context` (nothing to build a question from) | QUINN acknowledges it needs content to generate from, defers to ARIA | INFO | `suggested_handoff = 'aria'` |
| Medical-advice request mid-session | Declined, same as ARIA | WARN | `risk_level = 'high'` |

## Observability

### Logging

| Event | Level | Fields |
|-------|-------|--------|
| Question presented | INFO | agent_id, concept |
| Answer evaluated | INFO | agent_id, correct (bool), consecutive_wrong, consecutive_correct |
| Handoff suggested | INFO | agent_id, suggested_handoff, reason |

### Metrics

| Metric | Type | Labels |
|--------|------|--------|
| quinn_questions_presented_total | counter | concept |
| quinn_handoff_total | counter | target_agent |

## Acceptance Criteria

- [ ] **AC1:** Given no pending question in `episodic_context`, when QUINN responds, then it presents exactly one question and does not reveal the answer.
- [ ] **AC2:** Given a pending question and a student answer, when QUINN responds, then it confirms correct/incorrect and explains why the correct answer is right and why each distractor is wrong.
- [ ] **AC3:** Given `retrieved_chunks` used to construct the question, when QUINN presents it, then `AgentOutput.cited_chunks` references those chunk ids.
- [ ] **AC4:** Given 3 consecutive wrong answers on the same concept, when QUINN responds, then `AgentOutput.suggested_handoff == 'aria'`.
- [ ] **AC5:** Given 5+ completed questions with 80%+ accuracy and no frustration/consecutive-wrong condition met, when QUINN responds, then `AgentOutput.suggested_handoff == 'scout'`.
- [ ] **AC6:** Given the model's structured evaluation response reports `frustration_detected: true` (amended 2026-07-22 — originally "the last 3 messages score above the frustration threshold"), when QUINN responds, then `AgentOutput.suggested_handoff == 'mira'`, taking priority over any simultaneous accuracy/consecutive-wrong condition.
- [ ] **AC7:** Given a medical-advice request, when QUINN responds, then it's declined and `risk_level == 'high'`.
- [ ] **AC8:** Given any response, when inspected, then it never reveals the answer before an attempt, never skips distractor analysis, and never exceeds the student's mastery tier + 1.
- [ ] **AC9:** Given the full existing ARIA + MIRA test suite, when re-run after this change, then all 21 tests still pass unchanged (no regression).

## Domain Model

### Entities

| Entity | Definition | Spec Path | Status |
|--------|------------|-----------|--------|
| QUINN | The Practice Question Intelligence agent; third of 7 planned MCAT agents | specs/domain/definitions/quinn.md | New |

`specs/domain/glossary.md`'s "MCAT Domain Agents" table already lists QUINN ("Practice Questions — generates, curates, explains practice questions") — this change is its first implementation.

### Relationships

```text
ARIA ──suggested_handoff='quinn'──► QUINN (triggered)
QUINN ──reads (via episodic_context)──► concept ARIA just taught
QUINN ──suggested_handoff='aria'──► ARIA (3+ consecutive wrong)
QUINN ──suggested_handoff='scout'──► SCOUT (5+ questions, 80%+ accuracy) [SCOUT not yet implemented]
QUINN ──suggested_handoff='mira'──► MIRA (frustration > 0.6)
```

### Glossary

No new terms — QUINN, Handoff, BaseAgent, AgentInput, AgentOutput all pre-exist in `specs/domain/glossary.md`.

### Bounded Contexts

- **MCAT Agent Context**: ARIA, MIRA, QUINN (this change); SAGE, VERA, SCOUT, ATLAS referenced by id but not implemented.

## Specs Directory Changes

### Changes Summary

| Path | Action | Description |
|------|--------|--------------|
| specs/domain/definitions/quinn.md | Create | QUINN's identity, state machine, handoff thresholds, prohibited behaviors |

## Components

> Same gap as prior MCAT agent changes — no SDD component type for Python/FastAPI code in the active tech pack.

## System Analysis

### Inferred Requirements

- QUINN's `suggested_handoff = 'scout'` references an agent that doesn't exist yet — this change only sets the field; SCOUT itself is future work.
- The `episodic_context`/`session_notes` state-encoding pattern is now used by three agents (ARIA, MIRA, QUINN) for three different purposes. A dedicated, typed cross-turn-state contract field is increasingly worth formalizing (see Open Questions — this is the same open question raised in the MIRA change, now with a third data point).

### Gaps & Assumptions

- Assumes question-generation quality is out of scope — this is a mechanical scaffold, not exam-quality item writing (same assumption class as ARIA/MIRA's heuristic placeholders). **Amended 2026-07-22:** no longer accurate as a blanket statement — question wording, correctness reasoning, and distractor explanation prose now come from a real LLM call (FR2/FR3 amendments), not a template. Exam-quality *tuning* of that generation (prompt-engineering `quinn_v1.md` further, expanding beyond one distractor to full 4-option MCQs) remains unaddressed — see FR2 amendment's note on the kept single-distractor simplification.
- Assumes `StudentProfile` still has no per-concept mastery field (unchanged since the ARIA change) — difficulty bounding uses the same `episodic_context` mention-count proxy ARIA established.

### Cross-References

- `changes/2026/07/10/aria-agent/` — `BaseAgent`, contract mirrors, mastery-approximation pattern, and (as of 2026-07-22) the real-LLM-wiring pattern QUINN also follows (`LiteLLMGatewayClient`, `llm_support.py`). The frustration-*heuristic* pattern QUINN originally reused (`KeywordFrustrationEstimator`, imported directly from `aria.py`) no longer exists in either file — see FR4 amendment.
- `changes/2026/07/15/mira-agent/` — `episodic_context`-as-handoff-context pattern.
- `specs/domain/glossary.md` — pre-existing QUINN, Handoff entries.

## Requirements Discovery

### Questions & Answers

| Step | Question | Answer |
|------|----------|--------|
| Scope | How does QUINN hold state across a question/answer pair with no persistence layer? | Extend the session_notes/episodic_context marker pattern MIRA established, rather than adding new contract fields. |
| Scope | How good should generated question content be, given no LLM integration exists? | Deterministic templated placeholder, explicitly out of scope for quality — mechanical scaffold only. |

### User Feedback

- User specified QUINN's full identity, state machine expectations, handoff rules, and prohibited behaviors up front; approved the templated-placeholder/session_notes-state-reuse approach as proposed before this spec was written.

## Domain Updates

### Definition Specs

| File | Description | Action |
|------|-------------|--------|
| `quinn.md` | QUINN's full identity, state machine, handoff thresholds, prohibited behaviors | create |

## Testing Strategy

### Unit Tests

| Component | Test Case | Expected Behavior |
|-----------|-----------|--------------------|
| quinn.py | No pending question, `retrieved_chunks` provided, mocked question-generation response (amended 2026-07-22 — was a real templated call, now a mocked LLM completion) | Presents one question, answer withheld, `cited_chunks` populated (AC1, AC3) |
| quinn.py | Pending question + correct answer, mocked evaluation response (amended 2026-07-22) | Confirms correct, full distractor analysis given (AC2) |
| quinn.py | Pending question + incorrect answer, mocked evaluation response (amended 2026-07-22) | Confirms incorrect, full distractor analysis given (AC2) |
| quinn.py | 3 consecutive wrong on same concept | `suggested_handoff == 'aria'` (AC4) |
| quinn.py | 5+ questions, 80%+ accuracy, no frustration/wrong-streak | `suggested_handoff == 'scout'` (AC5) |
| quinn.py | Mocked evaluation response reports `frustration_detected: true` (amended 2026-07-22; was "frustration > 0.6") + simultaneous wrong-streak/accuracy condition | `suggested_handoff == 'mira'` wins (AC6) |
| quinn.py | Medical advice request | Declined, `risk_level == 'high'` (AC7) |
| quinn.py | Any response | No answer-before-attempt, no skipped distractor analysis, no over-tier question (AC8) |
| (full suite) | Re-run existing ARIA + MIRA tests | 21/21 still pass (AC9) |

### Test Data

| Entity | Required State | Purpose |
|--------|-----------------|---------|
| Fixture `episodic_context` with `quinn_pending` marker | Encodes a specific pending question + streak counters | AC2, AC4, AC5, AC6 |
| Fixture `retrieved_chunks` | Content to ground a fresh question | AC1, AC3 |

## Dependencies

### Internal Dependencies

| Component | Version | Reason |
|-----------|---------|--------|
| `changes/2026/07/10/aria-agent/` | Complete | `BaseAgent`, contract mirrors, `PromptRegistryClient`; originally also `KeywordFrustrationEstimator` (reused directly via import), removed 2026-07-22 when frustration detection moved to the LLM (FR4 amendment) — QUINN no longer imports anything frustration-related from `aria.py` |
| `changes/2026/07/15/mira-agent/` | Complete | `episodic_context`-as-state-channel pattern reused |

## Migration / Rollback

Nothing depends on QUINN yet (not served over HTTP) — revert the commit/PR to roll back.

## Out of Scope

- ~~Real, exam-quality MCAT question generation~~ — LiteLLM integration done 2026-07-22 (FR2 amendment); exam-quality *tuning* of that generation (beyond the kept single-distractor simplification) remains unaddressed.
- SCOUT itself (the handoff target for the accuracy milestone) — not implemented; this change only sets `suggested_handoff = 'scout'`.
- A dedicated typed "cross-turn state" contract field — this is the third agent to reuse the `episodic_context`/`session_notes` marker pattern; formalizing it is tracked as an Open Question, not built here.
- NEXUS/LangGraph/SSE wiring, real human-escalation wiring for `risk_level = 'high'` — same as prior MCAT agent changes.
- SAGE, VERA, ATLAS — the remaining unimplemented MCAT agents.

## Open Questions

- [ ] Now that ARIA, MIRA, and QUINN all reuse `episodic_context`/`session_notes` for different cross-turn state purposes, should a dedicated, typed contract field (or small set of fields) be added to `AgentInput`/`AgentOutput` to replace this pattern? (Raised in the MIRA change; now has a third data point.)
- [x] When should the templated `QuestionGenerator` placeholder be replaced with real LLM-backed question generation (LiteLLM)? **Resolved 2026-07-22** — see FR2 amendment.
- [x] Same open question as ARIA/MIRA: when should frustration/distress heuristics be replaced with a real signal source? **Resolved 2026-07-22** — see FR4 amendment; correctness grading and streak counters intentionally stayed deterministic (FR3 amendment explains why).
- [ ] New (2026-07-22): should QUINN's single-distractor `GeneratedQuestion` shape be expanded to full 4-option (A/B/C/D) MCQs, matching `quinn_v1.md`'s narrative description more closely? Kept as-is in the LLM-wiring change to stay scoped to "swap templates for real calls," not a redesign (see FR2 amendment).

## References

- `changes/2026/07/10/aria-agent/` — BaseAgent, contract mirrors, frustration-heuristic and mastery-approximation patterns
- `changes/2026/07/15/mira-agent/` — episodic_context-as-state-channel pattern
- `specs/domain/glossary.md` — pre-existing QUINN, Handoff entries
