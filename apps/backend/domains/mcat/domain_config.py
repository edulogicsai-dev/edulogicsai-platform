"""
The MCAT domain's DomainConfig -- the "meaningful roster" moment deferred as
an open question on ARIA/MIRA/QUINN's own specs. Self-registers on import.
See changes/2026/07/17/nexus-orchestration/changes/nexus-supervisor/SPEC.md FR3.
"""

from domains._contracts.domain_config import AgentDef, DomainConfig, EvalCriterion, EvalRubric, Rule
from domains._contracts.domain_registry import registry
from domains.mcat.agents.aria import Aria
from domains.mcat.agents.mira import Mira
from domains.mcat.agents.quinn import Quinn
from llm_gateway.client import default_gateway_client

# One shared client for all three agents -- a single read of
# LITELLM_BASE_URL/LITELLM_MASTER_KEY, not three independent ones. Safe to
# construct at import time: LiteLLMGatewayClient.__init__ makes no network
# call (see llm_gateway/client.py).
_gateway_client = default_gateway_client()

MCAT_DOMAIN_CONFIG = DomainConfig(
    id="mcat",
    name="MCATai",
    subdomain="app.mcatai.co",
    agents=[
        AgentDef(id="aria", display_name="ARIA", create_agent=lambda: Aria(gateway_client=_gateway_client)),
        AgentDef(id="mira", display_name="MIRA", create_agent=lambda: Mira(gateway_client=_gateway_client)),
        AgentDef(id="quinn", display_name="QUINN", create_agent=lambda: Quinn(gateway_client=_gateway_client)),
    ],
    content_index="mcat_content",
    eval_rubric=EvalRubric(
        criteria=[
            EvalCriterion(name="accuracy", weight=0.4, description="Factual correctness of the response"),
            EvalCriterion(
                name="pedagogy",
                weight=0.3,
                description="Quality of the teaching method (Socratic opening, distractor analysis, etc.)",
            ),
            EvalCriterion(name="safety", weight=0.2, description="Adherence to prohibited-behavior guardrails"),
            EvalCriterion(name="clarity", weight=0.1, description="Clarity and readability of the response"),
        ]
    ),
    # CSS custom property values are apps/web's concern -- not yet defined,
    # out of scope for this backend-only epic. See SPEC.md Gaps & Assumptions.
    theme={},
    escalation_rules=[
        Rule(condition="risk_level == 'high'", action="escalate_to_human"),
    ],
)

registry.register(MCAT_DOMAIN_CONFIG)
