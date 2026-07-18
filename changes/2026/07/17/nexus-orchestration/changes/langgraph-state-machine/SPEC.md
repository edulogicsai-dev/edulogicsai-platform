---
title: LangGraph State Machine
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

Build the LangGraph state machine that actually routes between ARIA, MIRA, and QUINN: one node per agent (dynamically built from `DomainConfig.agents`, never hardcoded), edges conditioned on `AgentOutput.suggested_handoff`, in-memory checkpointing so a session remembers which agent was last active across turns, and HITL escalation when `risk_level == 'high'`.

### Background

Unlike `litellm-gateway`/parts of `nexus-supervisor`, this change requires **no external credentials at all** — ARIA/MIRA/QUINN are fully deterministic Python (no live LLM calls), so the entire handoff cascade (including the "no cold starts" requirement) can be exercised for real, end-to-end, using the actual agent implementations, not mocks.

### Current State

`nexus-supervisor` provides `DomainConfig`/`DomainRegistry`/`assemble_agent_input`, but nothing actually invokes an agent or routes between them based on `suggested_handoff`. No LangGraph dependency exists yet.

---

## Functional Requirements

### FR1: Dynamic Graph Construction

**Behavior:**
- `apps/backend/nexus/graph_builder.py`'s `build_graph(domain_config, registry)` shall add exactly one LangGraph node per entry in `domain_config.agents` — the node function resolves the agent via `registry.resolve_agent(domain_config.id, agent_id)` and calls `agent.respond(...)`, never referencing an agent id as a literal outside the loop over `domain_config.agents`.

**Constraints:**
- Given a different `DomainConfig` with a different agent roster, the same function must produce a graph with a different node set — verified with a second, throwaway fake domain config in tests (not just re-testing MCAT).

### FR2: Handoff-Conditioned Edges, In-Turn Context Folding

**Behavior:**
- After a node runs, routing shall check the produced `AgentOutput.suggested_handoff`: if it names a different, valid (registered) agent, the graph transitions to that agent's node **within the same turn** (same `run_turn()` call, same student message) — not the next student message.
- Before invoking the next agent, the just-produced output's `session_notes` shall be folded into the carried-forward `AgentInput.episodic_context` as a new `EpisodicMemory` entry, so the handoff target agent has real context from this turn, not stale fixture data — this is what "no cold starts" means concretely (see epic AC2).
- If `suggested_handoff` is `null`, or names an agent already fully handled this turn beyond the hop limit (FR3), routing ends the turn.

### FR3: Max-Hops Safeguard

**Behavior:**
- A turn shall never cascade through more than `MAX_HOPS = 3` agent nodes, regardless of what `suggested_handoff` chains say — preventing an infinite handoff loop (e.g. a hypothetical agent pair that keep handing off to each other) from hanging a request.

### FR4: HITL Escalation

**Behavior:**
- If any node's output has `risk_level == 'high'`, the turn ends immediately at that node (no further handoff is followed, even if `suggested_handoff` is also set) and the turn result is marked `escalated=True`.
- An escalation event is logged (`logging.warning`, including `agent_id` and the triggering output) — no real paging/notification integration (see epic Out of Scope).

### FR5: In-Memory Checkpointing Across Turns

**Behavior:**
- The compiled graph shall use LangGraph's in-memory checkpointer (`MemorySaver`), keyed by `session_id` — so that if turn N ends with MIRA as the last active agent (no further handoff), turn N+1 (a new student message, same session) starts at MIRA rather than defaulting back to the domain's entry agent.
- Redis-backed checkpointing is explicitly deferred (see epic Out of Scope, per your "Phase 1" framing).

### FR6: Turn Runner

**Behavior:**
- `apps/backend/nexus/turn_runner.py`'s `run_turn(graph, session_id, agent_input, default_entry_agent_id)` shall: look up the session's last checkpointed agent (if any) as this turn's entry point, falling back to `default_entry_agent_id` for a fresh session; invoke the graph; return an ordered list of every `AgentOutput` produced this turn (so a caller can stream each in order, with visible `agent_id` changes) plus the `escalated` flag.

## Acceptance Criteria

- [ ] **AC1:** Given `build_graph` called with two different fake `DomainConfig`s (different agent rosters), when the resulting graphs are inspected, then their node sets differ accordingly — proving the construction is genuinely dynamic, not hardcoded to MCAT.
- [ ] **AC2:** Given real `AgentInput` that triggers ARIA's frustration-handoff condition (per `changes/2026/07/10/aria-agent/`'s existing test fixtures), when `run_turn` is called with the real MCAT graph, then it returns 2 outputs (ARIA's, then MIRA's), and MIRA's response acknowledges context that only exists because ARIA's `session_notes` were folded into `episodic_context` mid-turn — not stale/fixture data.
- [ ] **AC3:** Given a pathological fake domain config where two agents always hand off to each other, when `run_turn` is called, then it terminates after `MAX_HOPS` outputs, not indefinitely.
- [ ] **AC4:** Given real `AgentInput` that triggers both a `risk_level == 'high'` condition and (independently) a `suggested_handoff` on the same ARIA output (ARIA's medical-advice guard doesn't short-circuit its own frustration-handoff computation — both can be set on one output), when `run_turn` is called, then the turn ends at ARIA with `escalated=True`, and MIRA's node is never invoked.
- [ ] **AC5:** Given turn N ends with MIRA as the final active agent (no further handoff) for session `S`, when `run_turn` is called again for session `S` with a new message and no explicit entry override, then it starts at MIRA, not the domain's default entry agent.

## Technical Design

### Architecture

```
apps/backend/nexus/
├── graph_state.py     # GraphState (agent_input, current_agent_id, outputs, escalated, hops)
├── graph_builder.py   # build_graph(domain_config, registry)
└── turn_runner.py     # run_turn(graph, session_id, agent_input, default_entry_agent_id)
```

### Algorithms / Business Logic

**In-turn context folding** (FR2): after node N produces `output`, construct `EpisodicMemory(summary=output.session_notes or a truncated fallback of output.response, occurredAt=<now>, relevanceScore=1.0)` and append it to `agent_input.episodic_context` before the next node (if any) runs — this is a pure in-memory operation, no database involved (that's `database-wiring`'s job for cross-*session* persistence; this is cross-*agent-hop*, same-turn context passing).

**Escalation priority** (FR4): checked before handoff routing — `risk_level == 'high'` always wins over a simultaneously-set `suggested_handoff`, mirroring the same priority principle MIRA/QUINN's specs already established for their own internal handoff-priority logic (frustration/distress over other conditions).

## Testing Strategy

### Integration Tests (real agents, no mocks needed — no external credentials required)

| Test Case | Expected Behavior |
|-----------|--------------------|
| `build_graph` with two different fake domain configs | Different node sets (AC1) |
| Real ARIA→MIRA handoff via `run_turn` | 2 outputs, MIRA's response reflects this-turn context (AC2) |
| Pathological always-handoff fake domain config | Terminates at `MAX_HOPS` (AC3) |
| ARIA output with both `risk_level='high'` and `suggested_handoff` set | Turn ends at ARIA, MIRA never invoked (AC4) |
| Two sequential `run_turn` calls, same session, MIRA active after turn 1 | Turn 2 starts at MIRA (AC5) |

## Dependencies

### Internal Dependencies

| Component | Reason |
|-----------|--------|
| `nexus-supervisor` | `DomainConfig`, `DomainRegistry`, `assemble_agent_input` |
| ARIA, MIRA, QUINN | The actual agents this graph routes between |

### External Dependencies

| Library | Reason |
|---------|--------|
| `langgraph` | Graph construction, conditional edges, `MemorySaver` checkpointing |

## Out of Scope

- Redis-backed checkpointing.
- Real HITL notification/paging on escalation — logging only.
- Wiring `run_turn`'s output into an actual HTTP response — that's `sse-endpoint`.
- Persisting turn history to the database — that's `database-wiring` (this change's checkpointing is purely in-process, lost on process restart).

## References

- `changes/2026/07/17/nexus-orchestration/SPEC.md` — parent epic
- `changes/2026/07/17/nexus-orchestration/changes/nexus-supervisor/SPEC.md` — `DomainConfig`/`DomainRegistry` this builds on
- `specs/architecture/overview.md` — L2 Orchestration (NEXUS, LangGraph, HITL Escalation Bus)
