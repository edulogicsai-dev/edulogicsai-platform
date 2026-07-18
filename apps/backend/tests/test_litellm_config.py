from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "litellm.yaml"


def _load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text())


def test_config_has_expected_model_entries() -> None:
    config = _load_config()
    model_names = {entry["model_name"] for entry in config["model_list"]}
    assert model_names == {"haiku-intent", "sonnet-tutor", "sonnet-eval-batch"}


def test_no_hardcoded_api_keys() -> None:
    config = _load_config()
    for entry in config["model_list"]:
        api_key = entry["litellm_params"]["api_key"]
        assert api_key.startswith("os.environ/"), f"hardcoded key in {entry['model_name']}"


def test_sonnet_tutor_has_prompt_caching() -> None:
    config = _load_config()
    sonnet_tutor = next(e for e in config["model_list"] if e["model_name"] == "sonnet-tutor")
    assert "cache_control_injection_points" in sonnet_tutor["litellm_params"]
