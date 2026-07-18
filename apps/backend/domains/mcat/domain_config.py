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

MCAT_DOMAIN_CONFIG = DomainConfig(
    id="mcat",
    name="MCATai",
    subdomain="app.mcatai.co",
    agents=[
        AgentDef(id="aria", display_name="ARIA", create_agent=lambda: Aria()),
        AgentDef(id="mira", display_name="MIRA", create_agent=lambda: Mira()),
        AgentDef(id="quinn", display_name="QUINN", create_agent=lambda: Quinn()),
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
