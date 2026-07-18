---
title: NEXUS Supervisor
type: feature
status: active
domain: mcat
issue: TBD
created: 2026-07-17
updated: 2026-07-17
sdd_version: 7.3.0
parent_epic: ../../SPEC.md
affected_components: []
---

## Overview

Build the domain-agnostic NEXUS supervisor: a Python mirror of the TypeScript `DomainConfig`/`DomainRegistry` contract (`changes/2026/07/09/baseagent-domainconfig-contracts/`), the actual `domains/mcat` config registering ARIA/MIRA/QUINN, intent classification, `AgentInput` assembly, and a tenant-context helper. This is the piece that lets NEXUS "read `DomainConfig.agents` at boot" (per `CLAUDE.md`) instead of hardcoding a domain — the gap explicitly flagged when this epic was scoped.

### Background

`packages/core`'s `DomainConfig`/`AgentDef`/`DomainRegistry` (TypeScript) have no Python equivalent. All three MCAT agents exist and are unit-tested, but nothing loads them as a roster — each is only ever directly instantiated in its own test file. `domains/mcat/domain.config.ts` (the TypeScript registration) was explicitly deferred as an open question in all three agents' specs, pending "a meaningful roster" — with 3 agents now built, this is that moment, but on the Python side, since NEXUS itself is Python (per `CLAUDE.md`'s Agent Contract Architecture).

### Current State

No Python `DomainConfig`, no `DomainRegistry`, no `domains/mcat/domain_config.py`. ARIA/MIRA/QUINN are only ever constructed directly (`Aria()`, `Mira()`, `Quinn()`) in test files.

---

## Functional Requirements

### FR1: Python `DomainConfig` Mirror

**Behavior:**
- `apps/backend/domains/_contracts/domain_config.py` shall define `AgentDef`, `EvalCriterion`, `EvalRubric`, `Rule`, and `DomainConfig` as Python `dataclasses` (not Pydantic models — these are in-process configuration objects NEXUS loads at boot, not wire-format data crossing an HTTP boundary, unlike `AgentInput`/`AgentOutput`).
- `AgentDef` shall carry `id`, `display_name`, `create_agent: Callable[[], BaseAgent]` (a factory, matching the TypeScript version's `createAgent`), and optional `config: dict`.
- `DomainConfig` shall carry `id`, `name`, `subdomain`, `agents: list[AgentDef]`, `content_index`, `eval_rubric: EvalRubric`, `theme: dict[str, str]` (CSS custom properties), `escalation_rules: list[Rule]` — field-for-field matching `packages/core`'s TypeScript `DomainConfig`.

**Constraints:**
- No domain-specific fields (same constraint as the TypeScript original).

### FR2: `DomainRegistry` (Self-Registration)

**Behavior:**
- `apps/backend/domains/_contracts/domain_registry.py` shall define `DomainRegistry` with `register(config)`, `resolve_domain(domain_id) -> DomainLookupResult`, `resolve_agent(domain_id, agent_id) -> BaseAgent`, mirroring the TypeScript `DomainRegistry`'s behavior exactly: unknown domain lookups return a typed not-found result (never throw); unresolvable agents raise a typed `UnresolvedAgentError` identifying both ids.
- A module-level `registry` singleton is exported for domain packages to self-register against on import — same self-registration pattern as the TypeScript side (`changes/2026/07/09/baseagent-domainconfig-contracts/SPEC.md` FR3).

**Constraints:**
- Zero imports from any `domains/mcat` (or other domain) path in `domains/_contracts/`.

### FR3: `domains/mcat` Registration

**Behavior:**
- `apps/backend/domains/mcat/domain_config.py` shall construct a `DomainConfig` for `id='mcat'` with `agents=[aria, mira, quinn]` (each an `AgentDef` with a `create_agent` factory), `content_index='mcat_content'`, an `EvalRubric` with the 4 criteria already named in `specs/architecture/overview.md` (accuracy, pedagogy, safety, clarity), and one `Rule` for `risk_level == 'high'` → `escalate_to_human`.
- This module shall call `registry.register(...)` as an import-time side effect (self-registration).

**Constraints:**
- `theme` is an empty `dict` for now — real CSS theme values are `apps/web`'s concern, out of scope for this backend-only epic (see Gaps & Assumptions).

### FR4: Intent Classification

**Behavior:**
- `apps/backend/nexus/intent_classifier.py` shall define an `IntentClassifier` protocol: `async def classify(message: str, agent_ids: list[str]) -> str`, returning one of the given `agent_ids`.
- `KeywordIntentClassifier` (test double): a simple heuristic returning the first entry in `agent_ids` when no other signal is available — used in tests and as the default until a real key is available.
- `LiteLLMIntentClassifier` (real implementation): calls the `litellm-gateway`'s `haiku-intent` model via `LiteLLMGatewayClient.complete()`, prompting it to pick one of `agent_ids`; falls back to the first agent id if the model's response isn't a valid id. **Not exercised against a live key in this change** (see epic Requirements Discovery) — its logic is unit-tested against a mocked gateway client.

### FR5: `AgentInput` Assembly

**Behavior:**
- `apps/backend/nexus/supervisor.py`'s `assemble_agent_input(...)` shall construct a valid `AgentInput` from already-fetched components passed as arguments (`tenant_id`, `student_id`, `session_id`, `message`, `student_profile`, `session_history`, `retrieved_chunks`, `episodic_context`) — it does **not** fetch these itself.

**Constraints:**
- Actually fetching `student_profile`/`session_history`/`retrieved_chunks`/`episodic_context` from the database is `database-wiring`'s job (a later child in this epic) — `nexus-supervisor` defines the assembly contract, not the data access.

### FR6: Tenant Context Helper

**Behavior:**
- `apps/backend/nexus/tenant_context.py`'s `set_tenant_context(conn, tenant_id)` shall issue `SELECT set_config('app.tenant_id', $1, true)` against a given database connection, matching `core-data-schema`'s `current_tenant()` RLS mechanism (which reads `current_setting('app.tenant_id', true)`). **Discovered during implementation:** the originally-sketched `SET LOCAL app.tenant_id = $1` is not valid Postgres syntax — `SET`/`SET LOCAL` don't support bind parameters. `set_config(setting, value, is_local)` is a regular function call that does, and `is_local=true` gives identical transaction-scoped behavior.
- `conn` is typed as a minimal `Protocol` (an object with an `execute(query, *args)` method) — not a concrete database library type, so this function is testable with a mock connection here, and genuinely exercised against a real (local) connection in `database-wiring`.

### FR7: Zero Domain-Specific Logic

**Behavior:**
- `apps/backend/domains/_contracts/*.py` and `apps/backend/nexus/*.py` shall contain no references to `'aria'`, `'mira'`, `'quinn'`, or `'mcat'` as literal strings or imports — only `apps/backend/domains/mcat/domain_config.py` is allowed to name them.

## Acceptance Criteria

- [ ] **AC1:** Given the Python `DomainConfig` dataclasses, when compared field-for-field against `packages/core`'s TypeScript `DomainConfig`, then they match (id, name, subdomain, agents, contentIndex↔content_index, evalRubric↔eval_rubric, theme, escalationRules↔escalation_rules).
- [ ] **AC2:** Given `domains/mcat/domain_config.py` is imported, when `registry.resolve_domain('mcat')` is called, then it returns `found=True` with all 3 agents in its roster; `registry.resolve_agent('mcat', 'aria')` returns an `Aria` instance (and likewise for `mira`/`quinn`).
- [ ] **AC3:** Given `registry.resolve_agent('mcat', 'sage')` (an unregistered agent), when called, then it raises `UnresolvedAgentError` identifying `domain_id='mcat'`, `agent_id='sage'`.
- [ ] **AC4:** Given `KeywordIntentClassifier`, when `classify(message, ['aria', 'mira'])` is called, then it returns `'aria'` (first in the list).
- [ ] **AC5:** Given `LiteLLMIntentClassifier` with a mocked gateway client returning `'mira'`, when `classify(...)` is called, then it returns `'mira'`; given a mocked response of `'not-a-real-agent'`, then it falls back to the first agent id.
- [ ] **AC6:** Given all required components, when `assemble_agent_input(...)` is called, then it returns a valid `AgentInput` (Pydantic validation passes).
- [ ] **AC7:** Given a mock connection object, when `set_tenant_context(conn, 'mcat')` is called, then the mock's `execute` was called with `SELECT set_config('app.tenant_id', $1, true)` and `'mcat'`.
- [ ] **AC8:** Given `apps/backend/domains/_contracts/` and `apps/backend/nexus/`, when grepped for `'aria'`/`'mira'`/`'quinn'`/`'mcat'`, then no matches exist outside `domains/mcat/domain_config.py`.

## Technical Design

### Architecture

```
apps/backend/
├── domains/
│   ├── _contracts/
│   │   ├── domain_config.py      # AgentDef, DomainConfig, EvalRubric, Rule (dataclasses)
│   │   └── domain_registry.py    # DomainRegistry, UnresolvedAgentError, registry singleton
│   └── mcat/
│       ├── domain_config.py      # MCAT_DOMAIN_CONFIG, self-registers on import
│       └── agents/{aria,mira,quinn}.py   # existing
└── nexus/
    ├── intent_classifier.py      # IntentClassifier, KeywordIntentClassifier, LiteLLMIntentClassifier
    ├── supervisor.py             # assemble_agent_input()
    └── tenant_context.py         # set_tenant_context()
```

### Algorithms / Business Logic

**Self-registration boot sequence:** whatever entrypoint eventually starts NEXUS imports `domains.mcat.domain_config` (and, later, `domains.gre.domain_config`, etc.) — each import triggers `registry.register(...)` as a side effect. NEXUS itself never imports a domain package to build a static list; it only ever calls `registry.resolve_domain(tenant_id)`.

**Entry-point intent classification:** for a session with no active agent yet (fresh session), NEXUS classifies the student's first message against the domain's full agent roster (currently just `['aria', 'mira', 'quinn']`) to decide where to start — in practice this almost always resolves to `'aria'` (the primary tutor) since MIRA/QUINN are designed as handoff-only targets per their own specs, but the classification is genuine, not hardcoded.

## Gaps & Assumptions

- `theme: {}` (empty) for the MCAT `DomainConfig` — no real CSS theme values are defined anywhere yet; that's `apps/web`'s concern, out of scope for this backend epic.
- Since MIRA and QUINN are designed as handoff-only targets (per their own specs), the entry-point intent classifier will realistically almost always resolve to `'aria'` — this is expected, not a bug in the classifier.

## Testing Strategy

### Unit Tests

| Test Case | Expected Behavior |
|-----------|--------------------|
| `DomainConfig`/`AgentDef`/`EvalRubric`/`Rule` construction | AC1 |
| Import `domains.mcat.domain_config`, then `registry.resolve_domain('mcat')` | AC2 |
| `registry.resolve_agent('mcat', 'aria')` | Returns `Aria` instance (AC2) |
| `registry.resolve_agent('mcat', 'sage')` | Raises `UnresolvedAgentError` (AC3) |
| `KeywordIntentClassifier.classify(...)` | Returns first agent id (AC4) |
| `LiteLLMIntentClassifier.classify(...)` with mocked gateway | Returns model's choice or falls back (AC5) |
| `assemble_agent_input(...)` with all components | Valid `AgentInput` (AC6) |
| `set_tenant_context(mock_conn, 'mcat')` | Mock's `execute` called correctly (AC7) |
| grep audit | No domain-specific references outside `domains/mcat/` (AC8) |

## Dependencies

### Internal Dependencies

| Component | Reason |
|-----------|--------|
| `litellm-gateway` | `LiteLLMIntentClassifier` uses `LiteLLMGatewayClient` |
| `changes/2026/07/09/baseagent-domainconfig-contracts/` | TypeScript shape this mirrors |
| ARIA, MIRA, QUINN | Registered as the MCAT agent roster |

## Out of Scope

- Wiring `LiteLLMIntentClassifier` against a live Anthropic key.
- Actually fetching database context for `assemble_agent_input` — that's `database-wiring`.
- Actually executing `set_tenant_context` against a real connection — exercised end-to-end in `database-wiring`.
- GRE/DAT domain configs.

## References

- `changes/2026/07/17/nexus-orchestration/SPEC.md` — parent epic
- `changes/2026/07/09/baseagent-domainconfig-contracts/` — TypeScript `DomainConfig`/`DomainRegistry` this mirrors
- `changes/2026/07/10/aria-agent/`, `changes/2026/07/15/mira-agent/`, `changes/2026/07/15/quinn-agent/` — the 3 registered agents
