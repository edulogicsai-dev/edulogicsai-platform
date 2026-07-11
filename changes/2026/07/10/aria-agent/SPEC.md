---
title: ARIA — Adaptive Tutor Agent (MCAT)
type: feature
status: active
domain: mcat
issue: TBD
created: 2026-07-10
updated: 2026-07-10
sdd_version: 7.3.0
affected_components: []
---

## Overview

Implement ARIA — the primary adaptive Socratic tutor for MCATai, and the first of the 7 planned MCAT agents. Since `apps/backend` (the Python FastAPI runtime where domain agent logic actually lives, per `CLAUDE.md`'s hybrid TS/Python agent contract architecture) doesn't exist yet, this change also bootstraps a minimal FastAPI scaffold and the Pydantic contract mirrors ARIA conforms to.

### Background

> Why is this change needed? What problem does it solve?

`packages/core` (TypeScript) already defines the platform's agent contract types (`BaseAgent`, `AgentInput`, `AgentOutput`) — see the `baseagent-domainconfig-contracts` change. Those types are consumed by the frontend to parse SSE streams. Per `CLAUDE.md`'s Agent Contract Architecture (added as part of this change's scoping discussion): actual agent logic runs in Python on `apps/backend`, using Pydantic models that mirror the TypeScript shapes field-for-field — Python classes cannot literally `extend` a TypeScript class.

ARIA is the anchor tutor students interact with most: a warm, Socratic guide across all 4 MCAT sections, adapting depth to mastery and citing retrieved content. It's the natural first agent to build because it exercises the full contract (input consumption, RAG citation, handoff signaling, risk escalation) without depending on any other domain agent existing yet.

### Current State

> What exists today? What are the limitations?

- `apps/backend` does not exist at all — no `pyproject.toml`, no FastAPI app, no Python project structure of any kind.
- `domains/` (repository root) does not exist — no domain has prompts or config yet.
- `packages/core`'s TypeScript `AgentInput`/`AgentOutput`/`BaseAgent` exist and are stable (see `changes/2026/07/09/baseagent-domainconfig-contracts/`).
- `specs/domain/glossary.md` already lists ARIA ("Adaptive Tutor — Socratic method, explains concepts across all MCAT sections") among the 7 MCAT agents — this change is the first implementation of that entry.

---

## User Stories

- As a student, I want ARIA to ask a diagnostic question before explaining a new concept, so that the explanation meets me at my actual understanding rather than assuming a level.
- As a student, I want ARIA to explain at a depth that matches my mastery level, so that I'm neither bored by over-explanation nor lost from under-explanation.
- As a student, I want ARIA to cite the source material it draws from, so that I can trust and verify what I'm being taught.
- As a frustrated student, I want to be handed off to a motivation-focused agent (MIRA) rather than have ARIA keep pushing content at me.
- As a student who has demonstrated readiness, I want to be handed off to practice questions (QUINN) rather than keep receiving explanations I no longer need.
- As the platform, I want ARIA to refuse medical advice requests and flag them as high-risk, so that the platform never appears to offer medical diagnosis.

## Functional Requirements

### FR1: Backend Bootstrap

**Description:** Create a minimal `apps/backend` FastAPI/Python project — just enough to host the contract mirrors and ARIA, not a full production backend.

**Behavior:**
- `apps/backend/pyproject.toml` shall declare the project (Python 3.11+, per `CLAUDE.md`) with dependencies: `fastapi`, `uvicorn`, `pydantic` (v2), and dev dependencies `pytest`, `httpx` (for `TestClient`).
- `apps/backend/main.py` shall instantiate a FastAPI app with a single `GET /health` endpoint returning `{"status": "ok"}` — proof the scaffold boots, nothing more.
- No database, auth, or SSE streaming wiring in this change — those are separate, larger concerns (NEXUS, LangGraph orchestration, LiteLLM routing) tracked as follow-up work.

**Constraints:**
- No Node.js/Kubernetes/Helm tooling — this is a plain Python/pip project, matching Railway's deployment model for FastAPI per `CLAUDE.md`.

### FR2: Contract Mirrors

**Description:** Create Pydantic models mirroring `packages/core`'s TypeScript contract types field-for-field, plus a Python `BaseAgent` abstract base class with the same method surface (mirrored, not inherited across languages).

**Behavior:**
- `apps/backend/domains/_contracts/agent_io.py` shall define Pydantic models: `StudentProfile`, `Message`, `ContentChunk`, `EpisodicMemory`, `MasteryDelta`, `AgentInput`, `AgentOutput` — field names, types, and optionality matching `packages/core/src/agent/*.ts` exactly (snake_case fields: `tenant_id`, `student_id`, `session_id`, `message`, `student_profile`, `session_history`, `retrieved_chunks`, `episodic_context` on `AgentInput`; `response`, `agent_id`, `cited_chunks`, `suggested_handoff`, `mastery_update`, `session_notes`, `risk_level` on `AgentOutput`).
- `apps/backend/domains/_contracts/base_agent.py` shall define an abstract `BaseAgent` class mirroring `packages/core`'s TypeScript `BaseAgent`: abstract `fetch_prompt()`, `respond()`, `write_episodic_memory()`; concrete `stream()` orchestrating the three, matching the TypeScript version's control flow.
- A test shall assert the Pydantic `AgentInput`/`AgentOutput` field sets match a documented reference list (the same list this FR states above), so a future change to either the TypeScript or Python side that silently diverges the shape fails CI.

**Constraints:**
- These mirrors do not import from `packages/core` (impossible across languages) — shape equivalence is enforced by the test in the previous paragraph, not by shared code.
- No domain-specific fields on these mirror types (same constraint as the TypeScript originals).

### FR3: ARIA Identity & Core Behavior

**Description:** Implement `apps/backend/domains/mcat/agents/aria.py`, extending the Python `BaseAgent` (FR2).

**Behavior:**
- `respond()` shall, for any turn introducing content the student hasn't been assessed on yet, open with a diagnostic question before any explanation — never explain first. **Discovered during implementation:** `StudentProfile` (`packages/core`'s contract) has no per-concept mastery field, and `AgentOutput.mastery_update` is a single-event delta, not a queryable history — there is no field to check "prior `MasteryDelta` for this concept" against, as originally drafted here. Implemented instead as: infer a concept key from `retrieved_chunks`/`message`, and check whether any `EpisodicMemory.summary` in `episodic_context` mentions it — an interim heuristic, not a `student_profile` lookup (see Gaps & Assumptions, and `specs/domain/definitions/aria.md`).
- `respond()` shall be capable of addressing all 4 MCAT sections (Bio/Biochem, Chem/Physics, CARS, Psych/Soc) — section is inferred from `message`/`retrieved_chunks` content, not a separate input field.
- Explanation depth shall vary based on the student's mastery level for the relevant concept. **As implemented:** approximated by the count of prior `episodic_context` mentions of the inferred concept (more mentions → assume more familiarity → more concise explanation), not a `student_profile` field — same reason as above.
- `cited_chunks` on the returned `AgentOutput` shall reference `ContentChunk.id` values drawn from `retrieved_chunks` (the `mcat_content` RAG index) that were actually used in `response` — never empty when `retrieved_chunks` was non-empty and used.
- `fetch_prompt()` shall retrieve ARIA's system prompt via the `PromptRegistry` client abstraction (FR6), not by reading `domains/mcat/prompts/aria_v1.md` directly inline in `aria.py`.

**Constraints:**
- No hardcoded prompt text in `aria.py` (per `CLAUDE.md`: prompts never hardcoded).

### FR4: Handoff Rules

**Description:** ARIA shall set `AgentOutput.suggested_handoff` based on frustration and readiness signals.

**Behavior:**
- If a frustration estimate over the last 3 messages in `session_history` exceeds `0.6`, `suggested_handoff` shall be `'mira'`.
- If the student has completed 4 or more consecutive successful turns (tracked via a structured marker ARIA writes into `session_notes` each turn and reads back from `episodic_context` on the next), `suggested_handoff` shall be `'quinn'`.
- If neither condition holds, `suggested_handoff` shall be `null`.
- Frustration estimation and "successful turn" detection use an interim heuristic (keyword/pattern-based), exposed behind an injectable interface (`FrustrationEstimator`, `TurnOutcomeClassifier` protocols) so a future ML-based implementation (e.g. the SentimentTool referenced in `specs/architecture/overview.md`) can be substituted without changing `aria.py`'s handoff logic.

**Constraints:**
- Frustration/readiness detection logic must be deterministic and unit-testable (no live LLM call required to test handoff behavior).

### FR5: Prohibited Behaviors / Safety Guardrails

**Description:** ARIA shall refuse specific categories of request and never exhibit specific behaviors, regardless of prompt content.

**Behavior:**
- If `message` requests medical diagnosis or health advice, ARIA shall decline to answer the medical question and set `risk_level = 'high'` on the returned `AgentOutput`.
- ARIA shall never state or imply an MCAT score guarantee.
- ARIA shall never return an answer without an accompanying explanation.
- ARIA shall never skip the diagnostic-question opening when introducing a new (unassessed) concept (see FR3).

**Constraints:**
- The medical-advice refusal check runs independently of the LLM call (a guard checked against `message` before/around generation), so it cannot be bypassed by prompt injection alone — full jailbreak-resistance is out of scope; this is a first-layer guard, not the only one.

### FR6: Prompt Fetching Abstraction

**Description:** A minimal `PromptRegistry` client abstraction, with a file-based implementation for this change.

**Behavior:**
- `apps/backend/prompt_registry/client.py` shall define a `PromptRegistryClient` protocol with a `get_prompt(agent_id: str, version: str) -> str` method.
- `FilePromptRegistryClient` shall implement it by reading `domains/{domain}/prompts/{agent_id}_{version}.md` from disk.
- `domains/mcat/prompts/aria_v1.md` shall contain ARIA's full system prompt (identity, Socratic method instruction, section coverage, prohibited behaviors) — authored content, not generated by this spec.

**Constraints:**
- Full Langfuse-backed `PromptRegistry` (versioning, A/B testing, remote fetch) is explicitly out of scope — tracked as a follow-up (see Out of Scope).

## Non-Functional Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| Backend boots | `uvicorn main:app` starts without error, `GET /health` returns 200 | Manual/CI smoke test |
| Contract shape parity | Pydantic `AgentInput`/`AgentOutput` field sets match documented TypeScript reference | Automated test (FR2) |
| Handoff logic determinism | Same `session_history` input always yields same `suggested_handoff` | Unit tests |
| Test coverage | All FR3–FR5 behaviors have at least one passing test | pytest suite |

## Technical Design

### Architecture

```
apps/backend/
├── pyproject.toml
├── main.py                          # FastAPI app, GET /health
├── domains/
│   ├── _contracts/
│   │   ├── agent_io.py              # Pydantic mirrors (FR2)
│   │   └── base_agent.py            # Python BaseAgent ABC (FR2)
│   └── mcat/
│       └── agents/
│           └── aria.py              # ARIA (FR3–FR5)
├── prompt_registry/
│   └── client.py                    # PromptRegistryClient + FilePromptRegistryClient (FR6)
└── tests/
    ├── test_health.py
    ├── test_agent_io_contracts.py
    └── test_aria.py

domains/mcat/prompts/aria_v1.md      # ARIA's system prompt (repo root, per CLAUDE.md convention)
```

### Data Model

> No database schema changes — no persistence layer exists yet (the paused `core-data-schema` epic covers that). `student_profile`, `session_history`, `retrieved_chunks`, `episodic_context` arrive as `AgentInput` fields; this change doesn't define where they're fetched from.

**Modified Tables:** None.

### Algorithms / Business Logic

**Diagnostic-opening check:** For the concept(s) implied by `message`/`retrieved_chunks`, check `student_profile`/`episodic_context` for a prior `MasteryDelta` on that concept. If none exists, the response must open with a question, not an explanation.

**Frustration estimate (interim heuristic):** Given the last 3 `Message`s with `role == 'user'`, score simple lexical frustration markers (e.g. repeated punctuation, explicit frustration phrases) into a 0–1 estimate. This is a placeholder — see FR4 constraints and Out of Scope.

**Consecutive-successful-turns tracking:** ARIA writes a structured marker into `session_notes` each turn (e.g. `consecutive_successful_turns: N`). On the next turn, it reads the most recent such marker back from `episodic_context` to know the current streak, and increments or resets it based on a turn-outcome heuristic (placeholder — see FR4).

**Edge Cases:**
- Empty `session_history` (first-ever turn): frustration estimate and successful-turn streak both default to 0 — no handoff triggered on turn 1.
- `retrieved_chunks` empty: ARIA must not fabricate `cited_chunks`; it explains from general knowledge and `cited_chunks` is an empty list (not omitted).
- `message` contains both a medical-advice request and an in-scope MCAT question: the medical portion is declined and `risk_level = 'high'`; the in-scope portion may still be answered — the two aren't mutually exclusive within one turn.

## API Contract

- `GET /health` → `200 { "status": "ok" }` — the only HTTP endpoint added in this change. No agent-serving HTTP/SSE routes yet (that's NEXUS's job, out of scope — see Out of Scope).

## Security Considerations

- **Authentication:** N/A — no auth wiring in this change (bare FastAPI scaffold).
- **Authorization:** N/A — no multi-tenant routing yet.
- **Data Protection:** No PHI/health-advice content is generated or stored past declining it; `risk_level = 'high'` events are the observability hook for downstream HITL escalation (per `DomainConfig.escalationRules`, defined in the prior change but not wired to anything yet).
- **Input Validation:** All Pydantic models validate `AgentInput` shape at the boundary; malformed input raises a Pydantic `ValidationError` before reaching `aria.py`'s logic.

## Error Handling

| Error Scenario | User Message | Log Level | Recovery |
|----------------|--------------|-----------|----------|
| Malformed `AgentInput` (Pydantic validation failure) | N/A (rejected before agent logic runs) | ERROR | Caller (test harness / future NEXUS) surfaces a 422-equivalent |
| Medical-advice request detected | ARIA declines the medical portion, explains it's outside scope | INFO | `risk_level = 'high'` set for downstream HITL review |

## Observability

### Logging

| Event | Level | Fields |
|-------|-------|--------|
| Handoff suggested | INFO | agent_id, suggested_handoff, reason (frustration/readiness) |
| High-risk turn | WARN | agent_id, risk_level, reason (medical_advice_request) |

### Metrics

| Metric | Type | Labels |
|--------|------|--------|
| aria_handoff_total | counter | target_agent |
| aria_high_risk_total | counter | reason |

### Traces

> N/A — no tracing/Langfuse wiring in this change (bare scaffold).

## Acceptance Criteria

- [ ] **AC1:** Given `apps/backend` is freshly installed (`pip install -e .`), when `uvicorn main:app` is started and `GET /health` is called, then it returns `200 {"status": "ok"}`.
- [ ] **AC2:** Given the documented reference field list for `AgentInput`/`AgentOutput`, when the contract-parity test runs, then the Pydantic models' fields match it exactly.
- [ ] **AC3:** Given a student with no prior `MasteryDelta` for a concept, when ARIA responds to a message introducing that concept, then the response opens with a diagnostic question before any explanation.
- [ ] **AC4:** Given `retrieved_chunks` containing chunks ARIA draws on in its response, when ARIA responds, then `AgentOutput.cited_chunks` is non-empty and references chunk ids from `retrieved_chunks`.
- [ ] **AC5:** Given the last 3 user messages score above the frustration threshold, when ARIA responds, then `AgentOutput.suggested_handoff == 'mira'`.
- [ ] **AC6:** Given 4+ consecutive successful turns tracked via `session_notes`/`episodic_context`, when ARIA responds, then `AgentOutput.suggested_handoff == 'quinn'`.
- [ ] **AC7:** Given a message requesting medical diagnosis/advice, when ARIA responds, then the medical request is declined and `AgentOutput.risk_level == 'high'`.
- [ ] **AC8:** Given any response, when its content is inspected, then it never contains an MCAT score guarantee, is never an answer without explanation, and never skips the diagnostic opening for a new concept (FR3/FR5).

## Domain Model

> Comprehensive domain knowledge extracted from this change.

### Entities

| Entity | Definition | Spec Path | Status |
|--------|------------|-----------|--------|
| ARIA | The primary adaptive Socratic MCAT tutor agent; first of 7 planned MCAT agents | specs/domain/definitions/aria.md | New |

`specs/domain/glossary.md` already lists ARIA among the 7 MCAT agents (from an earlier commit) — this change is its first implementation, not a new glossary entry.

### Relationships

```text
ARIA ──extends──► BaseAgent (Python, apps/backend/domains/_contracts/base_agent.py)
ARIA ──consumes──► AgentInput (student_profile, session_history, retrieved_chunks, episodic_context)
ARIA ──produces──► AgentOutput (suggested_handoff → 'mira' | 'quinn' | null)
ARIA ──fetches via──► PromptRegistryClient ──reads──► domains/mcat/prompts/aria_v1.md
```

### Glossary

No new terms — `BaseAgent`, `AgentInput`, `AgentOutput`, `Handoff`, and `ARIA` itself are already defined in `specs/domain/glossary.md`. This change references them, doesn't redefine them.

### Bounded Contexts

- **MCAT Agent Context**: ARIA (this change); MIRA, QUINN, and the remaining 4 MCAT agents referenced by id but not implemented here.

## Specs Directory Changes

### Before

```text
specs/
├── architecture/
│   └── overview.md
└── domain/
    ├── glossary.md
    └── definitions/
        ├── base-agent.md
        ├── domain-config.md
        └── domain-registry.md
```

### After

```text
specs/
├── architecture/
│   └── overview.md
└── domain/
    ├── glossary.md
    └── definitions/
        ├── base-agent.md
        ├── domain-config.md
        ├── domain-registry.md
        └── aria.md              # NEW
```

### Changes Summary

| Path | Action | Description |
|------|--------|--------------|
| specs/domain/definitions/aria.md | Create | ARIA's identity, behavior rules, handoff thresholds, and prohibited behaviors, documented in full |

## Components

> No SDD component registered for this work — the active `fullstack-typescript` tech pack has no Python/FastAPI component type at all (same gap noted for `packages/core` in the prior change, now larger: an entire missing runtime, not just a missing package type).

### New Components

| Component | Type | Settings | Purpose |
|-----------|------|----------|---------|
| N/A | N/A | N/A | Not scaffolded via tech-pack component types (see Open Questions) |

### Modified Components

| Component | Changes |
|-----------|---------|
| N/A (apps/backend is net-new, untracked as an SDD component) | N/A |

## System Analysis

### Inferred Requirements

- A real sentiment/mastery-tracking model (replacing FR4's placeholder heuristics) will eventually be needed — this spec deliberately keeps that swappable via `FrustrationEstimator`/`TurnOutcomeClassifier` protocols rather than building it now.
- `domains/mcat/domain.config.ts` (registering ARIA + future agents in `DomainRegistry`) will need to exist once enough of the roster is built — explicitly deferred here (see Open Questions).

### Gaps & Assumptions

- Assumes Python 3.11+ and `pip` are available in the target environment (Railway, per `CLAUDE.md`); no assumption about `poetry`/`uv` — plain `pyproject.toml` + `pip install -e .`.
- Assumes `AgentInput.retrieved_chunks` arrives pre-populated (RAG retrieval already happened upstream, per `specs/architecture/overview.md`'s data flow) — ARIA does not perform retrieval itself.
- Assumes "successful turn" and "frustration" are approximated by heuristics for now, not a production ML model.
- Discovered during implementation: `StudentProfile` has no per-concept mastery field, so FR3's "mastery level from `student_profile`" and "prior `MasteryDelta`" language couldn't be implemented literally — both "concept previously assessed" and "explanation depth" are approximated via `episodic_context` mention counts instead (see FR3, updated to match).

### Cross-References

- `changes/2026/07/09/baseagent-domainconfig-contracts/` — the TypeScript contract this change mirrors in Python.
- `CLAUDE.md` — Agent Contract Architecture section (added during this change's scoping), Monorepo Structure, Naming Conventions.
- `specs/architecture/overview.md` — L3 Agent Fleet, Tool Registry (SentimentTool referenced as future replacement for FR4's heuristic).
- `specs/domain/glossary.md` — pre-existing ARIA, Handoff, Memory Tiers entries.

## Requirements Discovery

### Questions & Answers

| Step | Question | Answer |
|------|----------|--------|
| Scope | Is BaseAgent (TypeScript) directly extended by ARIA? | No — resolved to a hybrid architecture: TypeScript is the contract (frontend-consumed), Python is the implementation (Pydantic mirrors, no cross-language inheritance). CLAUDE.md updated accordingly. |
| Scope | Should this change bootstrap apps/backend from scratch? | Yes — minimal FastAPI scaffold, hand-authored plan (no tech-pack support for Python components). |
| Scope | Should domains/mcat/domain.config.ts (DomainConfig registration) be included? | No — deferred until a meaningful agent roster exists; tracked as an Open Question. |

### User Feedback

- User clarified the hybrid TS/Python architecture in detail (packages/core = contract types for frontend; apps/backend/domains/{domain}/agents/{name}.py = Python implementation via Pydantic mirrors) and asked CLAUDE.md to be updated to reflect it — done as part of this change's scoping, prior to SPEC.md creation.

## Domain Updates

### Glossary Terms

No changes — ARIA, BaseAgent, AgentInput, AgentOutput, Handoff are all pre-existing entries in `specs/domain/glossary.md`.

### Definition Specs

| File | Description | Action |
|------|-------------|--------|
| `aria.md` | ARIA's full identity, behavior rules, handoff thresholds, prohibited behaviors | create |

### Architecture Docs

- [ ] None required beyond the `CLAUDE.md` Agent Contract Architecture section already added during scoping.

## Testing Strategy

### Unit Tests

| Component | Test Case | Expected Behavior |
|-----------|-----------|--------------------|
| agent_io.py | Construct `AgentInput`/`AgentOutput` with the full documented field set | Validates successfully |
| agent_io.py | Field-set parity check against documented TypeScript reference | Matches exactly (AC2) |
| aria.py | Respond to a new (unassessed) concept | Opens with a diagnostic question (AC3) |
| aria.py | Respond with non-empty `retrieved_chunks` actually used | `cited_chunks` non-empty (AC4) |
| aria.py | Last 3 messages score above frustration threshold | `suggested_handoff == 'mira'` (AC5) |
| aria.py | 4+ consecutive successful turns tracked | `suggested_handoff == 'quinn'` (AC6) |
| aria.py | Message requests medical advice | Declined, `risk_level == 'high'` (AC7) |
| aria.py | Any response | No score guarantee, no unexplained answer, no skipped diagnostic opening (AC8) |
| prompt_registry/client.py | `FilePromptRegistryClient.get_prompt('aria', 'v1')` | Returns contents of `domains/mcat/prompts/aria_v1.md` |

### Integration Tests

| Scenario | Components | Expected Outcome |
|----------|------------|-------------------|
| N/A | N/A | No cross-service integration in this change (no NEXUS, no LLM gateway wiring yet) |

### E2E Tests

| User Flow | Steps | Expected Result |
|-----------|-------|------------------|
| N/A | N/A | No user-facing flow yet — ARIA isn't served over HTTP/SSE in this change |

### Test Data

| Entity | Required State | Purpose |
|--------|-----------------|---------|
| Fixture `AgentInput` (minimal valid) | Valid, minimal | Base fixture for all `aria.py` tests |
| Fixture `session_history` (3 frustrated messages) | Frustration markers present | AC5 |
| Fixture `episodic_context` (4 successful-turn markers) | `consecutive_successful_turns: 4` present | AC6 |

## Dependencies

### Internal Dependencies

| Component | Version | Reason |
|-----------|---------|--------|
| packages/core | N/A (reference only) | Python Pydantic mirrors must match its shape (FR2) |

### External Dependencies

| Service | API Version | Fallback |
|---------|--------------|----------|
| N/A | N/A | No external service calls in this change (no live LLM, no Langfuse) |

## Migration / Rollback

### Migration Steps

1. Create `apps/backend` scaffold.
2. Add contract mirrors and ARIA.
3. Add `domains/mcat/prompts/aria_v1.md`.

### Rollback Plan

1. Nothing yet depends on this (net-new, unserved over HTTP) — revert the commit/PR.

### Feature Flags

| Flag | Default | Purpose |
|------|---------|---------|
| N/A | N/A | Not applicable — not served over HTTP yet |

## Out of Scope

- `domains/mcat/domain.config.ts` (TypeScript `DomainConfig` registering ARIA in `DomainRegistry`) — deferred until a meaningful agent roster exists (see Open Questions).
- NEXUS orchestration, LangGraph state machine, LiteLLM routing, SSE serving of ARIA over HTTP — none of this exists yet; this change only builds ARIA as a directly-testable Python class.
- Full Langfuse-backed `PromptRegistry` (remote fetch, versioning, A/B testing) — `FilePromptRegistryClient` is a placeholder (FR6).
- Production-grade sentiment analysis / mastery-tracking ML models — FR4 uses interim heuristics behind swappable interfaces.
- The other 6 MCAT agents (QUINN, SAGE, VERA, MIRA, SCOUT, ATLAS) — referenced by id in handoff rules, not implemented.
- Any database/persistence layer — covered by the paused `core-data-schema` epic.

## Open Questions

- [ ] When should `domains/mcat/domain.config.ts` be created — after N more agents exist, or as soon as a second agent (e.g. MIRA, since ARIA's handoff rule already references it) is built?
- [ ] Should the frustration/readiness heuristics in FR4 be replaced by a real SentimentTool/ML model in the very next MCAT-agent change, or only once enough agents exist to justify the investment?

## References

- CLAUDE.md — Agent Contract Architecture, Monorepo Structure, Naming Conventions (updated during this change's scoping)
- `changes/2026/07/09/baseagent-domainconfig-contracts/` — TypeScript contract this change mirrors
- `specs/domain/glossary.md` — pre-existing ARIA, Handoff, Memory Tiers entries
- `specs/architecture/overview.md` — L3 Agent Fleet, Tool Registry
