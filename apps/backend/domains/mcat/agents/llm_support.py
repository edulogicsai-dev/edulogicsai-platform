"""
Shared LLM-calling plumbing for ARIA/MIRA/QUINN -- the low-level HTTP call
(LiteLLMGatewayClient.complete) and JSON-extraction concerns common to all
three, so each agent only owns its own prompt-assembly and JSON-shape
parsing. Not a domain-agnostic module (lives under domains/mcat/agents/, not
nexus/ or domains/_contracts/) -- see tests/test_no_domain_leakage.py.
"""

import json

from domains._contracts.agent_io import ContentChunk, EpisodicMemory, Message
from llm_gateway.client import LiteLLMGatewayClient

TUTOR_MODEL = "sonnet-tutor"


class LLMResponseParseError(Exception):
    """Raised when the model's completion isn't the JSON object its system
    prompt required. Left to propagate out of respond() -- sse-endpoint's
    existing event_stream() try/except (changes/2026/07/17/
    nexus-orchestration/changes/sse-endpoint/) already turns any exception
    raised mid-turn into a graceful `event: error`, so no new error-handling
    layer is added here."""


async def complete_json(
    gateway_client: LiteLLMGatewayClient,
    system_prompt: str,
    user_content: str,
    model: str = TUTOR_MODEL,
) -> dict:
    response = await gateway_client.complete(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    content = response["choices"][0]["message"]["content"]
    return _parse_json_object(content)


def _parse_json_object(content: str) -> dict:
    text = content.strip()
    # Claude sometimes wraps JSON in a markdown fence despite the system
    # prompt asking it not to -- strip that before parsing rather than
    # failing outright on an otherwise-valid response.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMResponseParseError(f"Model did not return valid JSON: {content!r}") from exc
    if not isinstance(parsed, dict):
        raise LLMResponseParseError(f"Model's JSON was not an object: {content!r}")
    return parsed


def render_chunks(chunks: list[ContentChunk]) -> str:
    if not chunks:
        return "(none retrieved)"
    return "\n".join(f"- [{c.id}] ({c.sourceId}): {c.text}" for c in chunks)


def render_episodic_context(episodic_context: list[EpisodicMemory]) -> str:
    if not episodic_context:
        return "(none yet -- first turn on record)"
    ordered = sorted(episodic_context, key=lambda m: m.occurredAt, reverse=True)
    return "\n".join(f"- {m.occurredAt}: {m.summary}" for m in ordered)


def render_session_history(messages: list[Message], limit: int = 6) -> str:
    recent = messages[-limit:]
    if not recent:
        return "(no prior turns this session)"
    return "\n".join(f"- {m.role}: {m.content}" for m in recent)


def valid_cited_chunks(reported: object, retrieved_chunks: list[ContentChunk]) -> list[str]:
    """Defensive filter: only ids the model could plausibly have cited
    survive, regardless of what the model's JSON reported -- a hallucinated
    chunk id must never reach AgentOutput.cited_chunks."""
    if not isinstance(reported, list):
        return []
    valid_ids = {c.id for c in retrieved_chunks}
    return [cid for cid in reported if isinstance(cid, str) and cid in valid_ids]


def as_bool(value: object, default: bool = False) -> bool:
    return value if isinstance(value, bool) else default


def as_risk_level(value: object, default: str = "low") -> str:
    return value if value in ("low", "medium", "high") else default


def as_str(value: object, default: str = "") -> str:
    return value if isinstance(value, str) else default
