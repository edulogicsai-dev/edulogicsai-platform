"""
Minimal PromptRegistry client abstraction. FilePromptRegistryClient is an
interim, file-based implementation -- full Langfuse-backed PromptRegistry
(remote fetch, versioning, A/B testing) is out of scope for this change.
See changes/2026/07/10/aria-agent/SPEC.md FR6.
"""

from pathlib import Path
from typing import Protocol

# apps/backend/prompt_registry/client.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]


class PromptRegistryClient(Protocol):
    def get_prompt(self, agent_id: str, version: str) -> str: ...


class FilePromptRegistryClient:
    def __init__(self, domain: str, prompts_root: Path = REPO_ROOT / "domains") -> None:
        self._domain = domain
        self._prompts_root = prompts_root

    def get_prompt(self, agent_id: str, version: str) -> str:
        path = self._prompts_root / self._domain / "prompts" / f"{agent_id}_{version}.md"
        return path.read_text()
