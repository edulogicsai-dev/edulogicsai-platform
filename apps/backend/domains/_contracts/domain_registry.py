"""
Python mirror of packages/core/src/domain/domain-registry.ts. Self-registration
pattern: each domains/<domain> package calls registry.register(...) as a side
effect of import. Zero imports from any domains/<domain> path in this module.
"""

from dataclasses import dataclass
from typing import Optional

from domains._contracts.base_agent import BaseAgent
from domains._contracts.domain_config import DomainConfig


class UnresolvedAgentError(Exception):
    def __init__(self, domain_id: str, agent_id: str) -> None:
        self.domain_id = domain_id
        self.agent_id = agent_id
        super().__init__(f'No registered constructor for agent "{agent_id}" in domain "{domain_id}"')


@dataclass
class DomainLookupResult:
    found: bool
    config: Optional[DomainConfig] = None


class DomainRegistry:
    def __init__(self) -> None:
        self._domains: dict[str, DomainConfig] = {}

    def register(self, config: DomainConfig) -> None:
        self._domains[config.id] = config

    def resolve_domain(self, domain_id: str) -> DomainLookupResult:
        config = self._domains.get(domain_id)
        return DomainLookupResult(found=True, config=config) if config else DomainLookupResult(found=False)

    def resolve_agent(self, domain_id: str, agent_id: str) -> BaseAgent:
        config = self._domains.get(domain_id)
        agent_def = next((a for a in (config.agents if config else []) if a.id == agent_id), None)
        if agent_def is None:
            raise UnresolvedAgentError(domain_id, agent_id)
        return agent_def.create_agent()


# Self-registration target -- domain packages import this and call .register(...).
registry = DomainRegistry()
