from prompt_registry.client import FilePromptRegistryClient


def test_file_prompt_registry_client_reads_aria_prompt() -> None:
    client = FilePromptRegistryClient(domain="mcat")
    prompt = client.get_prompt("aria", "v1")
    assert "ARIA" in prompt
    assert "diagnostic question" in prompt
