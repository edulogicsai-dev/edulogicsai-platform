# MIRA

## Definition

MIRA is the Motivation & Resilience Coach for MCATai — the second of the 7 planned MCAT agents, triggered when another agent (currently only ARIA) sets `suggested_handoff == 'mira'`. Implemented at `apps/backend/domains/mcat/agents/mira.py`, extending the same Python `BaseAgent` ARIA extends. Its system prompt lives at `domains/mcat/prompts/mira_v1.md`.

`specs/domain/glossary.md`'s "MCAT Domain Agents" table already lists MIRA ("Motivation Coach — detects frustration/burnout, provides encouragement") — this is its first implementation.

## Behavior

- **Acknowledge → validate → one strategy**, in that order, every turn. Never a generic acknowledgment, never a list of strategies.
- **Reads the handoff cause** from the most recent `episodic_context` entry (the same channel ARIA uses for its own `consecutive_successful_turns` marker — no dedicated "handoff context" field exists on `AgentInput` yet). Falls back to acknowledging `AgentInput.message` directly if `episodic_context` is empty.
- **Growth-mindset framing** — effort and strategy change outcomes; ability isn't fixed.
- **Not a tutor** — never introduces or continues MCAT content instruction; that stays ARIA's job.

## Handoff Rules

| Condition | Result |
|-----------|--------|
| Recovery signals in last 2 user messages | `suggested_handoff = 'aria'` |
| Distress estimate > 0.85 | `risk_level = 'high'` (human escalation signal, not an agent handoff) |
| Distress > 0.85 **and** recovery signals both present | `risk_level = 'high'` wins — safety takes priority over an ambiguous "feels better" signal |
| Neither | `suggested_handoff = null` (MIRA continues coaching) |
| Any condition | `suggested_handoff` is **never** `'quinn'` — a distressed/frustrated student never goes to practice questions |

## Prohibited Behaviors

- Therapy or mental health diagnosis.
- Minimizing the student's feelings.
- Pushing MCAT content while the student is emotionally overwhelmed.
- Promising a specific emotional outcome.

## Known Heuristic Placeholders

Distress estimation (`KeywordDistressEstimator`) and recovery-signal detection (`KeywordRecoverySignalClassifier`) are interim keyword heuristics, not ML models — isolated behind swappable protocols (`DistressEstimator`, `RecoverySignalClassifier`), mirroring the pattern established for ARIA's `FrustrationEstimator`/`TurnOutcomeClassifier`.

The `episodic_context`-based handoff-cause lookup (FR2) is itself a stopgap — if a third agent needs similar cross-agent context, a dedicated contract field should be considered instead (see `changes/2026/07/15/mira-agent/SPEC.md` Open Questions).

## Related

- [`BaseAgent`](./base-agent.md) — the contract MIRA implements (Python mirror), same as ARIA.
- [`ARIA`](./aria.md) — the agent that triggers MIRA via `suggested_handoff = 'mira'`, and the agent MIRA hands back to on recovery.
- `changes/2026/07/15/mira-agent/SPEC.md` — full specification.
