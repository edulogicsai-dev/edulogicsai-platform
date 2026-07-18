import pytest

import domains.mcat.domain_config  # noqa: F401 -- import triggers self-registration
from domains._contracts.domain_registry import UnresolvedAgentError, registry
from domains.mcat.agents.aria import Aria
from domains.mcat.agents.mira import Mira
from domains.mcat.agents.quinn import Quinn


def test_mcat_domain_resolves_with_all_three_agents() -> None:
    # AC2
    result = registry.resolve_domain("mcat")
    assert result.found is True
    agent_ids = {a.id for a in result.config.agents}
    assert agent_ids == {"aria", "mira", "quinn"}


def test_resolve_agent_returns_correct_instances() -> None:
    # AC2
    assert isinstance(registry.resolve_agent("mcat", "aria"), Aria)
    assert isinstance(registry.resolve_agent("mcat", "mira"), Mira)
    assert isinstance(registry.resolve_agent("mcat", "quinn"), Quinn)


def test_resolve_unregistered_agent_raises() -> None:
    # AC3
    with pytest.raises(UnresolvedAgentError) as exc_info:
        registry.resolve_agent("mcat", "sage")
    assert exc_info.value.domain_id == "mcat"
    assert exc_info.value.agent_id == "sage"


def test_resolve_unknown_domain_returns_not_found() -> None:
    result = registry.resolve_domain("gre")
    assert result.found is False
    assert result.config is None
