# QUINN

## Definition

QUINN is the Practice Question Intelligence agent for MCATai — the third of the 7 planned MCAT agents, triggered when ARIA sets `suggested_handoff == 'quinn'` after 4+ consecutive successful tutoring turns. Implemented at `apps/backend/domains/mcat/agents/quinn.py`, extending the same Python `BaseAgent` ARIA and MIRA extend. Its system prompt lives at `domains/mcat/prompts/quinn_v1.md`.

`specs/domain/glossary.md`'s "MCAT Domain Agents" table already lists QUINN ("Practice Questions — generates, curates, explains practice questions") — this is its first implementation.

## Behavior — Question/Answer State Machine

QUINN is the first MCAT agent requiring genuine multi-turn state (no persistence layer exists yet, so state is encoded into `session_notes` and read back via `episodic_context`, extending the pattern MIRA established):

- **No pending question found** in `episodic_context`: generate one question (templated placeholder, grounded in `retrieved_chunks`), present it, withhold the answer entirely, encode a `quinn_pending: {...}` JSON marker into `session_notes`.
- **Pending question found**: treat `AgentInput.message` as the student's attempt. Confirm correct/incorrect, give full distractor analysis (why the right answer is right, why the distractor is wrong) — every time, never skipped. Update streak counters (`consecutive_correct`, `consecutive_wrong`, `questions_completed`, `correct_count`).

Question difficulty is bounded to the student's mastery tier + 1, approximated via prior `episodic_context` mention counts for the concept (same proxy ARIA uses, since `StudentProfile` has no per-concept mastery field).

**Question generation is a deliberate placeholder** — a deterministic template, not real MCAT-quality item writing. Isolated behind a `QuestionGenerator` protocol for future LLM-backed replacement.

## Handoff Rules

| Condition | Result | Priority |
|-----------|--------|----------|
| Frustration estimate over last 3 messages > 0.6 (same heuristic as ARIA) | `suggested_handoff = 'mira'` | 1st |
| 3+ consecutive wrong on the same concept | `suggested_handoff = 'aria'` | 2nd |
| 5+ questions completed at 80%+ accuracy | `suggested_handoff = 'scout'` (SCOUT not yet implemented) | 3rd |
| None of the above | `suggested_handoff = null`, next question presented | — |

If multiple conditions fire simultaneously, the higher-priority one wins (frustration > re-teaching need > accuracy milestone) — safety and pedagogical need outrank a "doing well" signal.

## Prohibited Behaviors

- Revealing the answer before the student attempts the question.
- Skipping distractor analysis after any answer, correct or incorrect.
- Presenting a question above the student's mastery tier + 1.
- Providing medical advice or diagnosis (same guard as ARIA) — takes priority over the state machine; if triggered while a question is pending, that pending state is preserved unchanged rather than lost.

## Known Heuristic Placeholders / Open Design Questions

- `QuestionGenerator`'s templated implementation is explicitly not exam-quality — a stand-in pending real LLM integration.
- The `session_notes`/`episodic_context` JSON-marker pattern is now used by three agents (ARIA, MIRA, QUINN) for three different purposes. Worth formalizing into a typed contract field if a fourth agent needs the same thing (see `changes/2026/07/15/quinn-agent/SPEC.md` Open Questions).
- QUINN references `suggested_handoff = 'scout'` for an agent that doesn't exist yet, same pattern as ARIA referencing MIRA/QUINN before they were built.

## Related

- [`BaseAgent`](./base-agent.md) — the contract QUINN implements (Python mirror), same as ARIA/MIRA.
- [`ARIA`](./aria.md) — triggers QUINN via `suggested_handoff = 'quinn'`; QUINN hands back on 3+ consecutive wrong.
- [`MIRA`](./mira.md) — QUINN hands off to MIRA on frustration, same threshold/heuristic ARIA uses.
- `changes/2026/07/15/quinn-agent/SPEC.md` — full specification.
