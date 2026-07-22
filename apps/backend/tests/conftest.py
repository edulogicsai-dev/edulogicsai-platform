"""
Shared fixtures. mock_llm_transport intercepts every outgoing
LiteLLMGatewayClient.complete() HTTP call (regardless of which agent
instance made it -- LiteLLMGatewayClient.complete() constructs a fresh
httpx.AsyncClient per call, so patching the constructor globally, same
technique as test_llm_gateway_client.py's _patch_transport) and returns a
canned completion appropriate to which agent/phase is calling, inferred
from the system prompt actually sent.

Used by test_turn_runner.py and test_chat_endpoint.py, which exercise the
real MCAT_DOMAIN_CONFIG's Aria/Mira/Quinn end-to-end (no per-test
constructor injection point, unlike test_aria.py/test_mira.py/test_quinn.py
which construct agents directly). The "understanding" this fake applies is
deliberately the same keyword signal the old heuristics used -- these
integration tests were written against fixtures crafted with those exact
phrases; the real model's judgment is exercised separately in
test_aria.py/test_mira.py/test_quinn.py via arbitrary canned JSON, not
inferred from message content.
"""

import json

import httpx
import pytest

FRUSTRATION_MARKERS = [
    "i give up",
    "so frustrating",
    "i don't get it",
    "i hate this",
    "so confused",
    "i'm lost",
    "why is this so hard",
]

RECOVERY_MARKERS = [
    "feeling better",
    "let's try again",
    "i'm ready",
    "that helps",
    "feel calmer",
    "let's continue",
]

DISTRESS_MARKERS = [
    "can't do this anymore",
    "i'm worthless",
    "what's the point",
    "want to quit",
    "i'm a failure",
    "nothing works",
    "can't take it",
]


def _contains_any(text: str, markers: list[str]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def _student_only_text(user_content: str) -> str:
    """Restrict marker matching to the student's own words -- "- user: ..."
    lines from render_session_history plus the "Student's message: ..."
    line -- not the full rendered blob, which also contains assistant
    lines (the old keyword classifiers filtered to
    `role == "user"` messages only; matching against the whole blob would
    false-positive on assistant text, e.g. "Let's try again.")."""
    lines = []
    for line in user_content.splitlines():
        stripped = line.strip()
        if stripped.startswith("- user:") or stripped.startswith("Student's message:"):
            lines.append(stripped)
    return "\n".join(lines)


def _fake_llm_response(system_prompt: str, user_content: str) -> dict:
    student_text = _student_only_text(user_content)

    if "Presenting a New Question" in system_prompt:
        return {
            "prompt_text": (
                'True or false: this accurately describes the concept. '
                "Take your time -- what's your answer?"
            ),
            "correct_answer": "true",
            "correct_reason": "it reflects the retrieved material",
            "distractor": "false",
            "distractor_reason": "it contradicts the retrieved material",
            "cited_chunks": [],
        }
    if "Evaluating an Answer" in system_prompt:
        return {
            "explanation": (
                'Correct! "true" is right because it reflects the retrieved material. '
                '"false" is wrong because it contradicts the retrieved material.'
            ),
            "frustration_detected": _contains_any(student_text, FRUSTRATION_MARKERS),
        }
    if "You are MIRA" in system_prompt:
        distressed = _contains_any(student_text, DISTRESS_MARKERS)
        # test_turn_runner.py's "no cold start" AC checks that MIRA's
        # response reflects the dynamically-folded episodic context (ARIA's
        # session_notes from *this* turn), not stale data -- a real LLM
        # would paraphrase rather than quote verbatim, so this fake
        # deliberately echoes the handoff-cause line Mira.respond() put
        # first in its user_content, to keep that guarantee genuinely
        # tested rather than assuming exact-string LLM reproduction.
        first_line = user_content.splitlines()[0] if user_content else ""
        handoff_cause = first_line.split(": ", 1)[1] if ": " in first_line else first_line
        return {
            "response": (
                f"What you're carrying ({handoff_cause}) sounds like more than I'm equipped "
                "to help with alone -- I want to make sure a person can check in with you about this."
                if distressed
                else f"I hear you -- {handoff_cause} is genuinely hard, and the effort you've put "
                "in matters. Here's one thing that might help: take a short break, then come back to it."
            ),
            "recovered": _contains_any(student_text, RECOVERY_MARKERS) and not distressed,
            "risk_level": "high" if distressed else "low",
            "session_notes": "distress observed" if distressed else "offered a break",
        }
    # ARIA (or any other sonnet-tutor caller using the ARIA-shaped contract)
    return {
        "response": "Let's work through this together -- what do you already know here?",
        "cited_chunks": [],
        "frustration_detected": _contains_any(student_text, FRUSTRATION_MARKERS),
        "risk_level": "low",
    }


def _handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    messages = body.get("messages", [])
    system_prompt = messages[0]["content"] if messages else ""
    user_content = messages[1]["content"] if len(messages) > 1 else ""
    payload = _fake_llm_response(system_prompt, user_content)
    return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(payload)}}]})


@pytest.fixture
def mock_llm_transport(monkeypatch):
    """Only injects the mock transport when the caller didn't already
    specify one -- test_chat_endpoint.py's own client fixture constructs
    its httpx.AsyncClient with an explicit ASGITransport (to call the app
    under test in-process); that must keep working. LiteLLMGatewayClient
    never passes `transport=` itself, so this only intercepts its calls."""
    transport = httpx.MockTransport(_handler)
    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        if "transport" not in kwargs:
            kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)
