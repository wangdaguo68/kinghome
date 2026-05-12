import os
from pathlib import Path

import pytest

from zen_trader.config import Settings, load_settings


def test_load_defaults():
    config_path = Path(__file__).parent.parent / "config.yaml"
    settings = load_settings(str(config_path))
    assert isinstance(settings, Settings)
    assert settings.ai.provider == "anthropic"
    assert settings.ai.model == "claude-sonnet-4-20250514"
    assert settings.retry.max_attempts == 3
    assert "xiaohongshu" in settings.platforms.enabled


def test_cli_overrides():
    config_path = Path(__file__).parent.parent / "config.yaml"
    settings = load_settings(str(config_path), cli_overrides={
        "provider": "openai",
        "model": "gpt-4o",
        "platforms": "xiaohongshu,weibo",
    })
    assert settings.ai.provider == "openai"
    assert settings.ai.model == "gpt-4o"
    assert settings.platforms.enabled == ["xiaohongshu", "weibo"]


def test_env_api_keys():
    os.environ["ANTHROPIC_API_KEY"] = "test-key-123"
    os.environ["OPENAI_API_KEY"] = "test-openai-key"
    config_path = Path(__file__).parent.parent / "config.yaml"
    settings = load_settings(str(config_path))
    assert settings.anthropic_api_key == "test-key-123"
    assert settings.openai_api_key == "test-openai-key"
