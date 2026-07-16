from prompt_registry.client import FilePromptRegistryClient


def test_file_prompt_registry_client_reads_aria_prompt() -> None:
    client = FilePromptRegistryClient(domain="mcat")
    prompt = client.get_prompt("aria", "v1")
    assert "ARIA" in prompt
    assert "diagnostic question" in prompt


def test_file_prompt_registry_client_reads_mira_prompt() -> None:
    # FR5: MIRA reuses the same client, no new code -- just a different agent_id.
    client = FilePromptRegistryClient(domain="mcat")
    prompt = client.get_prompt("mira", "v1")
    assert "MIRA" in prompt


def test_file_prompt_registry_client_reads_quinn_prompt() -> None:
    client = FilePromptRegistryClient(domain="mcat")
    prompt = client.get_prompt("quinn", "v1")
    assert "QUINN" in prompt
