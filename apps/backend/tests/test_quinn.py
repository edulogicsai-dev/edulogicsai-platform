import json

import pytest

from domains._contracts.agent_io import (
    AgentInput,
    ContentChunk,
    EpisodicMemory,
    Message,
    StudentProfile,
)
from domains.mcat.agents.quinn import PENDING_MARKER_PREFIX, Quinn


def make_input(**overrides) -> AgentInput:
    defaults = dict(
        tenant_id="mcat",
        student_id="student-1",
        session_id="session-1",
        message="enzyme kinetics",
        student_profile=StudentProfile(
            userId="student-1", displayName="Alex", createdAt="2026-01-01T00:00:00Z"
        ),
        session_history=[],
        retrieved_chunks=[],
        episodic_context=[],
    )
    defaults.update(overrides)
    return AgentInput(**defaults)


def make_pending_memory(**overrides) -> EpisodicMemory:
    payload = dict(
        concept="enzyme_kinetics",
        correct_answer="true",
        correct_reason="it reflects the retrieved material on enzyme_kinetics",
        distractor="false",
        distractor_reason="it contradicts the retrieved material on enzyme_kinetics",
        consecutive_correct=0,
        consecutive_wrong=0,
        questions_completed=0,
        correct_count=0,
    )
    payload.update(overrides)
    return EpisodicMemory(
        id="mem-1",
        summary=PENDING_MARKER_PREFIX + json.dumps(payload),
        occurredAt="2026-01-01T00:00:00Z",
        relevanceScore=0.9,
    )


DEFAULT_QUESTION_PAYLOAD = {
    "prompt_text": 'True or false: "Enzymes lower activation energy" accurately describes enzyme kinetics. Take your time -- what\'s your answer?',
    "correct_answer": "true",
    "correct_reason": "it reflects the retrieved material on enzyme_kinetics",
    "distractor": "false",
    "distractor_reason": "it contradicts the retrieved material on enzyme_kinetics",
    "cited_chunks": ["chunk-1"],
}


def _correct_evaluation_payload(frustration_detected: bool = False) -> dict:
    return {
        "explanation": (
            'Correct! "true" is right because it reflects the retrieved material on '
            'enzyme_kinetics. "false" is wrong because it contradicts the retrieved '
            "material on enzyme_kinetics."
        ),
        "frustration_detected": frustration_detected,
    }


def _incorrect_evaluation_payload(frustration_detected: bool = False) -> dict:
    return {
        "explanation": (
            'Not quite. "true" is right because it reflects the retrieved material on '
            'enzyme_kinetics. "false" is wrong because it contradicts the retrieved '
            "material on enzyme_kinetics."
        ),
        "frustration_detected": frustration_detected,
    }


class _FakeGatewayClient:
    """Returns question_payload for question-generation calls (system prompt
    contains QUESTION_JSON_CONTRACT's marker) and evaluation_payload for
    answer-evaluation calls -- distinguished by the distinct required-keys
    each contract asks for, mirroring how the real prompts differ."""

    def __init__(self, question_payload: dict = None, evaluation_payload: dict = None) -> None:
        self._question_payload = question_payload or DEFAULT_QUESTION_PAYLOAD
        self._evaluation_payload = evaluation_payload

    async def complete(self, model: str, messages: list[dict]) -> dict:
        system_prompt = messages[0]["content"]
        if "Evaluating an Answer" in system_prompt:
            payload = self._evaluation_payload or _correct_evaluation_payload()
        else:
            payload = self._question_payload
        return {"choices": [{"message": {"content": json.dumps(payload)}}]}


def make_quinn(question_payload: dict = None, evaluation_payload: dict = None) -> Quinn:
    return Quinn(gateway_client=_FakeGatewayClient(question_payload, evaluation_payload))


async def respond_once(input: AgentInput, quinn: Quinn = None):
    quinn = quinn or make_quinn()
    async for output in quinn.respond(input):
        return output
    raise AssertionError("respond() yielded no output")


@pytest.mark.asyncio
async def test_no_pending_question_presents_one_question_and_withholds_answer():
    # AC1, AC3
    input = make_input(
        retrieved_chunks=[
            ContentChunk(id="chunk-1", text="Enzymes lower activation energy.", sourceId="enzyme_kinetics", score=0.9)
        ]
    )
    output = await respond_once(input)
    lowered = output.response.lower()
    # The question format itself says "true or false" -- that's not an answer
    # reveal. What must NOT appear is the evaluative verdict language.
    assert "correct!" not in lowered
    assert "not quite" not in lowered
    assert "is right because" not in lowered
    assert output.cited_chunks == ["chunk-1"]
    assert output.suggested_handoff is None


@pytest.mark.asyncio
async def test_correct_answer_gives_full_distractor_analysis():
    # AC2
    input = make_input(message="true", episodic_context=[make_pending_memory()])
    output = await respond_once(input, make_quinn(evaluation_payload=_correct_evaluation_payload()))
    lowered = output.response.lower()
    assert "correct" in lowered
    assert "is right because" in lowered
    assert "is wrong because" in lowered


@pytest.mark.asyncio
async def test_incorrect_answer_gives_full_distractor_analysis():
    # AC2
    input = make_input(message="false", episodic_context=[make_pending_memory()])
    output = await respond_once(input, make_quinn(evaluation_payload=_incorrect_evaluation_payload()))
    lowered = output.response.lower()
    assert "not quite" in lowered
    assert "is right because" in lowered
    assert "is wrong because" in lowered


@pytest.mark.asyncio
async def test_three_consecutive_wrong_triggers_aria_handoff():
    # AC4
    input = make_input(
        message="false",
        episodic_context=[make_pending_memory(consecutive_wrong=2, consecutive_correct=0)],
    )
    output = await respond_once(input, make_quinn(evaluation_payload=_incorrect_evaluation_payload()))
    assert output.suggested_handoff == "aria"


@pytest.mark.asyncio
async def test_five_questions_at_high_accuracy_triggers_scout_handoff():
    # AC5
    input = make_input(
        message="true",
        episodic_context=[
            make_pending_memory(questions_completed=4, correct_count=4, consecutive_wrong=0)
        ],
    )
    output = await respond_once(input, make_quinn(evaluation_payload=_correct_evaluation_payload()))
    assert output.suggested_handoff == "scout"


@pytest.mark.asyncio
async def test_frustration_wins_over_simultaneous_wrong_streak():
    # AC6 -- frustration now comes from the model's own judgment (req 6),
    # not a keyword list; the fake simply reports it, as the real model would.
    session_history = [
        Message(role="user", content="i don't get it at all", timestamp="2026-01-01T00:00:00Z"),
        Message(role="user", content="this is so frustrating", timestamp="2026-01-01T00:01:00Z"),
        Message(role="user", content="i give up, i'm lost", timestamp="2026-01-01T00:02:00Z"),
    ]
    input = make_input(
        message="false",
        session_history=session_history,
        episodic_context=[make_pending_memory(consecutive_wrong=2)],
    )
    output = await respond_once(
        input, make_quinn(evaluation_payload=_incorrect_evaluation_payload(frustration_detected=True))
    )
    assert output.suggested_handoff == "mira"


@pytest.mark.asyncio
async def test_medical_advice_request_declined_with_high_risk():
    # AC7 -- deterministic guard, no LLM call happens on this path at all.
    input = make_input(message="Do I have appendicitis based on this pain?")
    output = await respond_once(input)
    assert output.risk_level == "high"
    assert "can't offer medical diagnosis" in output.response.lower()


@pytest.mark.asyncio
async def test_medical_advice_preserves_pending_question_state():
    # AC7 + no state loss
    pending_memory = make_pending_memory(consecutive_correct=2)
    input = make_input(
        message="What medication should I take for this headache?",
        episodic_context=[pending_memory],
    )
    output = await respond_once(input)
    assert output.risk_level == "high"
    assert output.session_notes == pending_memory.summary
    preserved = json.loads(output.session_notes[len(PENDING_MARKER_PREFIX):])
    assert preserved["consecutive_correct"] == 2


@pytest.mark.asyncio
async def test_never_reveals_answer_before_attempt_and_never_exceeds_tier():
    # AC8
    output = await respond_once(make_input())
    # The fresh-question response must not contain the evaluative verdicts
    # ("correct!"/"not quite") that only appear once an answer is evaluated.
    lowered = output.response.lower()
    assert "correct!" not in lowered
    assert "not quite" not in lowered


@pytest.mark.asyncio
async def test_never_skips_distractor_analysis_when_handing_off():
    # AC8 -- even when a handoff is triggered, the explanation for the
    # triggering answer must still be given in full.
    input = make_input(
        message="false",
        episodic_context=[make_pending_memory(consecutive_wrong=2)],
    )
    output = await respond_once(input, make_quinn(evaluation_payload=_incorrect_evaluation_payload()))
    assert output.suggested_handoff == "aria"
    lowered = output.response.lower()
    assert "is right because" in lowered
    assert "is wrong because" in lowered


@pytest.mark.asyncio
async def test_correct_streak_continues_with_llm_generated_next_question():
    # Not previously covered: the "continue" path (no handoff) must call the
    # generator again for a real next question, appended after the explanation.
    input = make_input(message="true", episodic_context=[make_pending_memory()])
    next_question_payload = {
        "prompt_text": 'True or false: "Vmax is unchanged by competitive inhibition." Take your time -- what\'s your answer?',
        "correct_answer": "true",
        "correct_reason": "competitive inhibitors are overcome by excess substrate",
        "distractor": "false",
        "distractor_reason": "that's true of non-competitive inhibition instead",
        "cited_chunks": [],
    }
    quinn = Quinn(
        gateway_client=_FakeGatewayClient(
            question_payload=next_question_payload,
            evaluation_payload=_correct_evaluation_payload(),
        )
    )
    output = await respond_once(input, quinn)
    assert output.suggested_handoff is None
    assert "Vmax is unchanged" in output.response
    assert output.session_notes.startswith(PENDING_MARKER_PREFIX)
