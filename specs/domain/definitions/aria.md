# ARIA

## Definition

ARIA is the primary adaptive Socratic tutor for MCATai — the first of the 7 planned MCAT agents. Implemented at `apps/backend/domains/mcat/agents/aria.py`, extending the Python `BaseAgent` (mirroring `packages/core`'s TypeScript contract; see `specs/domain/definitions/base-agent.md`). Its system prompt lives at `domains/mcat/prompts/aria_v1.md`.

`specs/domain/glossary.md` already lists ARIA among the 7 MCAT agents ("Adaptive Tutor — Socratic method, explains concepts across all MCAT sections") — this is its first implementation.

## Behavior

- **Diagnostic opening:** For any concept the student hasn't previously been assessed on (no matching prior mention in `episodic_context`), ARIA opens with a diagnostic question before explaining.
- **Section coverage:** All 4 MCAT sections (Bio/Biochem, Chem/Physics, CARS, Psych/Soc) — section is inferred from message/retrieved content, not a separate input field.
- **Mastery-adapted depth:** Explanation depth varies based on how many prior mentions of a concept appear in `episodic_context` (an interim heuristic — see Gaps below).
- **RAG citation:** `AgentOutput.cited_chunks` references `ContentChunk.id` values from `AgentInput.retrieved_chunks` actually used in the response; never fabricated, never omitted when chunks were used.

## Handoff Rules

| Condition | `suggested_handoff` |
|-----------|----------------------|
| Frustration estimate over last 3 user messages > 0.6 | `'mira'` |
| 4+ consecutive successful turns (tracked via a `consecutive_successful_turns: N` marker ARIA writes into `session_notes` and reads back from `episodic_context`) | `'quinn'` |
| Neither | `null` |

Frustration wins if both conditions would otherwise apply (checked first).

## Prohibited Behaviors

- Medical diagnosis or health advice — declined, `risk_level = 'high'`.
- MCAT score guarantees.
- Answers without an accompanying explanation.
- Skipping the diagnostic opening for a new (unassessed) concept.

## Known Heuristic Placeholders

Frustration detection (`KeywordFrustrationEstimator`), turn-outcome classification (`KeywordTurnOutcomeClassifier`), and concept-mastery depth adaptation are all interim keyword/pattern heuristics, not ML models — deliberately isolated behind swappable protocols (`FrustrationEstimator`, `TurnOutcomeClassifier`) so a real `SentimentTool` (referenced in `specs/architecture/overview.md`'s Tool Registry) or `concept_mastery` DB-backed signal can replace them later without changing ARIA's handoff/depth logic itself.

## Related

- [`BaseAgent`](./base-agent.md) — the contract ARIA implements (Python mirror).
- `changes/2026/07/10/aria-agent/SPEC.md` — full specification.
