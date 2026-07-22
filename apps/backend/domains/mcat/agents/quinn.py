"""
QUINN -- the Practice Question Intelligence agent for MCATai.
See changes/2026/07/15/quinn-agent/SPEC.md (FR1-FR5) and
domains/mcat/prompts/quinn_v1.md for QUINN's authored system prompt.

Question generation and answer-evaluation text now call Claude (via
LiteLLMGatewayClient, model alias "sonnet-tutor") -- see LLMQuestionGenerator
and Quinn._evaluate_answer below, and llm_support.py for the shared
JSON-completion plumbing. Cross-turn state (pending question, streak
counters, ease factor) stays deterministic Python bookkeeping, encoded into
session_notes/episodic_context exactly as before: correctness is an exact
string match against the stored correct_answer (grading a known MCQ answer
doesn't benefit from an LLM's judgment, and the ease-factor/streak math must
be exactly reproducible turn to turn). Frustration detection for the
MIRA handoff, like ARIA's, now comes from the model's own understanding of
the message rather than a keyword list.
"""

import datetime
import json
import re
from dataclasses import dataclass
from typing import AsyncIterator, List, Optional, Protocol

from domains._contracts.agent_io import AgentInput, AgentOutput, ContentChunk, EpisodicMemory, MasteryDelta
from domains._contracts.base_agent import BaseAgent
from domains.mcat.agents.llm_support import (
    complete_json,
    render_chunks,
    render_session_history,
    valid_cited_chunks,
    as_bool,
    as_str,
)
from llm_gateway.client import LiteLLMGatewayClient, default_gateway_client
from prompt_registry.client import FilePromptRegistryClient, PromptRegistryClient

MEDICAL_ADVICE_PATTERNS = [
    r"\bshould i (take|see a doctor)\b",
    r"\bdo i have\b",
    r"\bwhat medication\b",
    r"\bcan you diagnose\b",
    r"\bmy (symptom|diagnosis|prescription)\b",
]

PENDING_MARKER_PREFIX = "quinn_pending: "
DEFAULT_EASE_FACTOR = 2.5
MAX_EASE_FACTOR = 3.0
MIN_EASE_FACTOR = 1.3

QUESTION_JSON_CONTRACT = """

## Required Response Format (Presenting a New Question -- Phase 1)

Respond with ONLY a single JSON object -- no markdown code fences, no prose \
outside the JSON. Use exactly these keys:

{
  "prompt_text": "<the question itself, presented per Phase 1 -- end with \
'Take your time -- what's your answer?'. Never reveal the answer here.>",
  "correct_answer": "<the correct answer, exactly as the student should type it back>",
  "correct_reason": "<why the correct answer is correct>",
  "distractor": "<one plausible wrong answer>",
  "distractor_reason": "<why that wrong answer is tempting but incorrect>",
  "cited_chunks": ["<chunk_id>", "..."]
}
"""

EVALUATION_JSON_CONTRACT = """

## Required Response Format (Evaluating an Answer -- Phase 2)

Respond with ONLY a single JSON object -- no markdown code fences, no prose \
outside the JSON. Use exactly these keys:

{
  "explanation": "<Phase 2 evaluation per the guidance above -- confirm \
correct/incorrect immediately, then full distractor analysis for both the \
correct answer and the wrong one, every time, even when a handoff follows>",
  "frustration_detected": true or false -- true only if the signals \
described in \"When to Hand Off > To MIRA\" are present in the student's \
recent messages
}
"""


def _adjust_ease_factor(previous: float, correct: bool) -> float:
    """
    Same simplified SM-2-style rule as ConceptMasteryRepository.record_attempt
    (changes/2026/07/17/nexus-orchestration/changes/database-wiring/) --
    computed here too so QUINN can embed it in mastery_update immediately,
    without waiting on a database round-trip. See that change's SPEC.md FR4.
    """
    if correct:
        return min(previous + 0.1, MAX_EASE_FACTOR)
    return max(previous - 0.2, MIN_EASE_FACTOR)


@dataclass
class GeneratedQuestion:
    concept: str
    prompt_text: str
    correct_answer: str
    correct_reason: str
    distractor: str
    distractor_reason: str
    cited_chunk_ids: List[str]


class QuestionGenerator(Protocol):
    async def generate(
        self, system_prompt: str, concept: str, chunks: List[ContentChunk], difficulty_tier: int
    ) -> GeneratedQuestion: ...


class LLMQuestionGenerator:
    def __init__(self, gateway_client: LiteLLMGatewayClient) -> None:
        self._gateway_client = gateway_client

    async def generate(
        self, system_prompt: str, concept: str, chunks: List[ContentChunk], difficulty_tier: int
    ) -> GeneratedQuestion:
        user_content = (
            f"Concept to test: {concept}\n"
            f"Difficulty tier (0 = most basic; never exceed one tier above the "
            f"student's demonstrated level): {difficulty_tier}\n\n"
            f"Retrieved content to ground the question in:\n{render_chunks(chunks)}\n\n"
            f"Generate ONE new question per Phase 1 of your question cycle."
        )
        parsed = await complete_json(self._gateway_client, system_prompt + QUESTION_JSON_CONTRACT, user_content)
        return GeneratedQuestion(
            concept=concept,
            prompt_text=as_str(parsed.get("prompt_text")),
            correct_answer=as_str(parsed.get("correct_answer")),
            correct_reason=as_str(parsed.get("correct_reason")),
            distractor=as_str(parsed.get("distractor")),
            distractor_reason=as_str(parsed.get("distractor_reason")),
            cited_chunk_ids=valid_cited_chunks(parsed.get("cited_chunks"), chunks),
        )


def _is_medical_advice_request(message: str) -> bool:
    lowered = message.lower()
    return any(re.search(pattern, lowered) for pattern in MEDICAL_ADVICE_PATTERNS)


def _infer_concept(input: AgentInput) -> str:
    if input.retrieved_chunks:
        return input.retrieved_chunks[0].sourceId.lower()
    return input.message.strip().lower()[:64]


def _count_prior_mentions(concept: str, episodic_context: List[EpisodicMemory]) -> int:
    return sum(1 for mem in episodic_context if concept in mem.summary.lower())


def _decode_pending_marker(summary: str) -> Optional[dict]:
    if not summary.startswith(PENDING_MARKER_PREFIX):
        return None
    try:
        return json.loads(summary[len(PENDING_MARKER_PREFIX) :])
    except json.JSONDecodeError:
        return None


def _find_pending_question(episodic_context: List[EpisodicMemory]) -> Optional[dict]:
    for mem in sorted(episodic_context, key=lambda m: m.occurredAt, reverse=True):
        payload = _decode_pending_marker(mem.summary)
        if payload is not None:
            return payload
    return None


def _encode_pending_marker(question: GeneratedQuestion, streaks: dict) -> str:
    payload = {
        "concept": question.concept,
        "correct_answer": question.correct_answer,
        "correct_reason": question.correct_reason,
        "distractor": question.distractor,
        "distractor_reason": question.distractor_reason,
        **streaks,
    }
    return PENDING_MARKER_PREFIX + json.dumps(payload)


class Quinn(BaseAgent):
    id = "quinn"

    def __init__(
        self,
        prompt_client: Optional[PromptRegistryClient] = None,
        gateway_client: Optional[LiteLLMGatewayClient] = None,
        question_generator: Optional[QuestionGenerator] = None,
    ) -> None:
        self._prompt_client = prompt_client or FilePromptRegistryClient(domain="mcat")
        self._gateway_client = gateway_client or default_gateway_client()
        self._generator = question_generator or LLMQuestionGenerator(self._gateway_client)

    async def fetch_prompt(self) -> str:
        return self._prompt_client.get_prompt("quinn", "v1")

    async def respond(self, input: AgentInput) -> AsyncIterator[AgentOutput]:
        pending = _find_pending_question(input.episodic_context)

        if _is_medical_advice_request(input.message):
            # Medical guard takes priority, independent of pending-question state
            # (FR5) -- preserve any pending question unchanged rather than losing it.
            preserved_notes = PENDING_MARKER_PREFIX + json.dumps(pending) if pending else ""
            yield AgentOutput(
                response=(
                    "I can't offer medical diagnosis or health advice -- that's outside what "
                    "I'm able to help with. Let's get back to practice when you're ready."
                ),
                agent_id=self.id,
                cited_chunks=[],
                suggested_handoff=None,
                mastery_update=None,
                session_notes=preserved_notes,
                risk_level="high",
            )
            return

        if pending is None:
            async for output in self._present_fresh_question(input):
                yield output
            return

        async for output in self._evaluate_answer(input, pending):
            yield output

    async def _present_fresh_question(self, input: AgentInput) -> AsyncIterator[AgentOutput]:
        concept = _infer_concept(input)
        difficulty_tier = _count_prior_mentions(concept, input.episodic_context)
        base_prompt = await self.fetch_prompt()
        question = await self._generator.generate(base_prompt, concept, input.retrieved_chunks, difficulty_tier)
        streaks = {
            "consecutive_correct": 0,
            "consecutive_wrong": 0,
            "questions_completed": 0,
            "correct_count": 0,
            "ease_factor": DEFAULT_EASE_FACTOR,
        }
        yield AgentOutput(
            response=question.prompt_text,
            agent_id=self.id,
            cited_chunks=question.cited_chunk_ids,
            suggested_handoff=None,
            mastery_update=None,
            session_notes=_encode_pending_marker(question, streaks),
            risk_level="low",
        )

    async def _evaluate_answer(
        self, input: AgentInput, pending: dict
    ) -> AsyncIterator[AgentOutput]:
        is_correct = input.message.strip().lower() == str(pending["correct_answer"]).strip().lower()

        consecutive_correct = pending["consecutive_correct"] + 1 if is_correct else 0
        consecutive_wrong = pending["consecutive_wrong"] + 1 if not is_correct else 0
        questions_completed = pending["questions_completed"] + 1
        correct_count = pending["correct_count"] + (1 if is_correct else 0)
        accuracy = correct_count / questions_completed if questions_completed else 0.0

        previous_ease_factor = float(pending.get("ease_factor", DEFAULT_EASE_FACTOR))
        new_ease_factor = _adjust_ease_factor(previous_ease_factor, is_correct)
        # MasteryDelta.previousStability/newStability are repurposed to carry
        # ease-factor values, not true FSRS stability -- see SPEC.md FR4 and
        # core-data-schema's concept-mastery SPEC.md for the underlying
        # discrepancy this continues rather than hides.
        # concept_mastery's concept_id column requires the domain::slug
        # convention (specs/domain/glossary.md; enforced by a DB check
        # constraint -- discovered when this was first wired to the real
        # table). QUINN's own internal concept tracking (pending["concept"],
        # used in student-facing response text) deliberately stays
        # unprefixed; the domain prefix is added only here, at the DB-write
        # boundary, so students never see "mcat::" in a response.
        mastery_update = MasteryDelta(
            conceptId=f"{input.tenant_id}::{pending['concept']}",
            previousStability=previous_ease_factor,
            newStability=new_ease_factor,
            reviewedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

        base_prompt = await self.fetch_prompt()
        eval_user_content = (
            f"The student answered: {input.message}\n"
            f"This answer was {'CORRECT' if is_correct else 'INCORRECT'}.\n"
            f"Correct answer: \"{pending['correct_answer']}\" -- {pending['correct_reason']}\n"
            f"Incorrect option to analyze: \"{pending['distractor']}\" -- {pending['distractor_reason']}\n\n"
            f"Recent conversation this session:\n{render_session_history(input.session_history, limit=4)}"
        )
        parsed = await complete_json(
            self._gateway_client, base_prompt + EVALUATION_JSON_CONTRACT, eval_user_content
        )
        explanation = as_str(parsed.get("explanation"))
        frustration_detected = as_bool(parsed.get("frustration_detected"))

        suggested_handoff: Optional[str] = None
        if frustration_detected:
            suggested_handoff = "mira"
        elif consecutive_wrong >= 3:
            suggested_handoff = "aria"
        elif questions_completed >= 5 and accuracy >= 0.8:
            suggested_handoff = "scout"

        streaks = {
            "consecutive_correct": consecutive_correct,
            "consecutive_wrong": consecutive_wrong,
            "questions_completed": questions_completed,
            "correct_count": correct_count,
            "ease_factor": new_ease_factor,
        }

        if suggested_handoff is not None:
            yield AgentOutput(
                response=explanation,
                agent_id=self.id,
                cited_chunks=[],
                suggested_handoff=suggested_handoff,
                mastery_update=mastery_update,
                session_notes=json.dumps(streaks),
                risk_level="low",
            )
            return

        concept = str(pending["concept"])
        next_question = await self._generator.generate(base_prompt, concept, input.retrieved_chunks, consecutive_correct)
        yield AgentOutput(
            response=f"{explanation} {next_question.prompt_text}",
            agent_id=self.id,
            cited_chunks=next_question.cited_chunk_ids,
            suggested_handoff=None,
            mastery_update=mastery_update,
            session_notes=_encode_pending_marker(next_question, streaks),
            risk_level="low",
        )

    async def write_episodic_memory(self, input: AgentInput, output: AgentOutput) -> None:
        # No persistence layer exists yet (paused core-data-schema epic).
        # Placeholder no-op -- see SPEC.md Out of Scope.
        return None
