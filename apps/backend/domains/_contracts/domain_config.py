"""
Python mirror of packages/core/src/domain/domain-config.ts (TypeScript).
These are in-process configuration objects NEXUS loads at boot -- not
wire-format data crossing an HTTP boundary (unlike AgentInput/AgentOutput,
which are Pydantic) -- so they're plain dataclasses.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

from domains._contracts.base_agent import BaseAgent


@dataclass
class AgentDef:
    id: str
    display_name: str
    create_agent: Callable[[], BaseAgent]
    config: Optional[dict] = None


@dataclass
class EvalCriterion:
    name: str
    weight: float
    description: str


@dataclass
class EvalRubric:
    criteria: list[EvalCriterion] = field(default_factory=list)


@dataclass
class Rule:
    condition: str
    action: str
    threshold: Optional[float] = None


@dataclass
class DomainConfig:
    id: str
    name: str
    subdomain: str
    agents: list[AgentDef]
    content_index: str
    eval_rubric: EvalRubric
    theme: dict[str, str]  # CSS custom property name/value pairs
    escalation_rules: list[Rule]
