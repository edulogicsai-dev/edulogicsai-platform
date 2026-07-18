---
title: LiteLLM Gateway
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

Configure the LiteLLM proxy (`apps/backend/config/litellm.yaml`) and a thin Python client for talking to it — model routing (Haiku for intent classification, Sonnet for tutoring), prompt caching, a Batch API config stub for future EVAL work, and a health-check path. Per `CLAUDE.md`'s rule "All LLM calls route through LiteLLM — never direct Anthropic SDK," this is the only place `apps/backend` is allowed to reach an LLM from.

### Background

No LLM gateway exists yet. ARIA/MIRA/QUINN's `respond()` methods are entirely deterministic placeholders (keyword heuristics) — none of them call an LLM. This change doesn't change that (see Out of Scope) — it builds the gateway infrastructure `nexus-supervisor`'s intent classification will sit behind.

### Current State

No `config/`, no LiteLLM dependency, no LLM client code anywhere in `apps/backend`.

---

## Functional Requirements

### FR1: LiteLLM Proxy Config

**Behavior:**
- `apps/backend/config/litellm.yaml` shall declare two model aliases: `haiku-intent` (routes to an Anthropic Haiku model) and `sonnet-tutor` (routes to an Anthropic Sonnet model), both reading their API key from `os.environ/ANTHROPIC_API_KEY` (never hardcoded, per `CLAUDE.md`).
- `sonnet-tutor` shall have `cache_control_injection_points` configured for system-message prompt caching (Anthropic prompt caching, exposed via LiteLLM).
- A `sonnet-eval-batch` model alias shall exist as a **stub** for the future EVAL agent's Batch API usage (50% cost discount) — declared in config, not invoked by any code in this change (see Out of Scope).

### FR2: Gateway Client

**Behavior:**
- `apps/backend/llm_gateway/client.py` shall define `LiteLLMGatewayClient`, an async HTTP client (via `httpx`) targeting the LiteLLM proxy's OpenAI-compatible surface: `health()` (calls the proxy's `/health` route) and `complete(model, messages)` (calls `/chat/completions`).
- The client takes `base_url` and an optional `api_key` as constructor arguments — no hardcoded proxy URL or key.

### FR3: Health Check

**Behavior:**
- `LiteLLMGatewayClient.health()` returns `True` only on a `200` response from the proxy's `/health` endpoint, `False` otherwise (including connection errors, not raised exceptions — a health check that throws isn't useful to a caller checking readiness).

## Acceptance Criteria

- [ ] **AC1:** Given `apps/backend/config/litellm.yaml`, when parsed as YAML, then it contains `haiku-intent`, `sonnet-tutor`, and `sonnet-eval-batch` model entries, none with a hardcoded API key.
- [ ] **AC2:** Given `sonnet-tutor`'s config, when inspected, then it has `cache_control_injection_points` configured.
- [ ] **AC3:** Given a mocked `200 {"status": "healthy"}` response from `/health`, when `LiteLLMGatewayClient.health()` is called, then it returns `True`.
- [ ] **AC4:** Given a mocked connection failure, when `LiteLLMGatewayClient.health()` is called, then it returns `False` without raising.
- [ ] **AC5:** Given a mocked `200` response from `/chat/completions`, when `LiteLLMGatewayClient.complete()` is called, then it returns the parsed JSON body.

## Technical Design

### `apps/backend/config/litellm.yaml`

```yaml
model_list:
  - model_name: haiku-intent
    litellm_params:
      model: anthropic/claude-3-5-haiku-20241022
      api_key: os.environ/ANTHROPIC_API_KEY

  - model_name: sonnet-tutor
    litellm_params:
      model: anthropic/claude-sonnet-4-20250514
      api_key: os.environ/ANTHROPIC_API_KEY
      cache_control_injection_points:
        - location: message
          role: system

  # Stub for future EVAL agent batch jobs (50% cost discount) -- not invoked
  # by any code in this change. See changes/.../litellm-gateway/SPEC.md Out of Scope.
  - model_name: sonnet-eval-batch
    litellm_params:
      model: anthropic/claude-sonnet-4-20250514
      api_key: os.environ/ANTHROPIC_API_KEY
      mode: batch

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
```

### `apps/backend/llm_gateway/client.py` (sketch)

```python
import httpx

class LiteLLMGatewayClient:
    def __init__(self, base_url: str, api_key: str | None = None):
        self._base_url = base_url
        self._api_key = api_key

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(base_url=self._base_url) as client:
                resp = await client.get("/health")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def complete(self, model: str, messages: list[dict]) -> dict:
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.post(
                "/chat/completions", json={"model": model, "messages": messages}, headers=headers
            )
            resp.raise_for_status()
            return resp.json()
```

## Testing Strategy

### Unit Tests

| Test Case | Expected Behavior |
|-----------|--------------------|
| `litellm.yaml` parses, has 3 model entries, no hardcoded keys | AC1 |
| `sonnet-tutor` has `cache_control_injection_points` | AC2 |
| `health()` against `httpx.MockTransport` returning 200 | Returns `True` (AC3) |
| `health()` against a transport raising a connection error | Returns `False`, no exception (AC4) |
| `complete()` against a mocked 200 JSON response | Returns parsed body (AC5) |

## Dependencies

### Internal Dependencies

None — first change in this epic.

### External Dependencies

| Service | Reason | Fallback in this change |
|---------|--------|--------------------------|
| Anthropic API (via LiteLLM proxy) | Actual model calls | Not exercised live — `httpx.MockTransport` stands in for the proxy in all tests (see epic SPEC.md Requirements Discovery) |

## Out of Scope

- Actually running the LiteLLM proxy process — this change writes its config and a client for it, not a running deployment.
- Any code that calls `sonnet-eval-batch` — stub only, for the future EVAL agent.
- Cost tracking / Langfuse observability wiring.
- Testing against a real Anthropic API key.

## References

- `changes/2026/07/17/nexus-orchestration/SPEC.md` — parent epic
- `CLAUDE.md` — "All LLM calls route through LiteLLM — never direct Anthropic SDK"
