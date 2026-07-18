from domains._contracts.domain_config import AgentDef, DomainConfig, EvalCriterion, EvalRubric, Rule
from domains._contracts.base_agent import BaseAgent


class _FakeAgent(BaseAgent):
    id = "fake"

    async def fetch_prompt(self):
        return ""

    async def respond(self, input):
        return
        yield  # pragma: no cover

    async def write_episodic_memory(self, input, output):
        return None


def test_domain_config_field_parity_with_typescript_contract() -> None:
    # AC1: id, name, subdomain, agents, contentIndex<->content_index,
    # evalRubric<->eval_rubric, theme, escalationRules<->escalation_rules
    config = DomainConfig(
        id="fake-domain",
        name="Fake Domain",
        subdomain="app.fake.co",
        agents=[AgentDef(id="fake", display_name="Fake", create_agent=lambda: _FakeAgent())],
        content_index="fake_content",
        eval_rubric=EvalRubric(criteria=[EvalCriterion(name="accuracy", weight=1.0, description="x")]),
        theme={"--color-primary": "#000"},
        escalation_rules=[Rule(condition="risk_level == 'high'", action="escalate_to_human")],
    )
    assert config.id == "fake-domain"
    assert config.content_index == "fake_content"
    assert config.eval_rubric.criteria[0].name == "accuracy"
    assert config.theme["--color-primary"] == "#000"
    assert config.escalation_rules[0].action == "escalate_to_human"
    assert config.agents[0].create_agent().id == "fake"
