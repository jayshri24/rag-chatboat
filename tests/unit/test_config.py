import os
import pytest
from unittest.mock import patch
from app.config import Settings, load_settings


def test_settings_with_valid_env():
    """Test loading settings from environment variables."""
    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-key-123",
        "OPENAI_MODEL": "gpt-4",
    }):
        s = Settings()
        assert s.openai_api_key == "test-key-123"
        assert s.openai_model == "gpt-4"


def test_settings_with_defaults():
    """Test defaults for optional settings."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}):
        s = Settings()
        assert s.openai_model == "gpt-4o-mini"


def test_load_settings_function():
    """Test load_settings returns a Settings instance."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}):
        s = load_settings()
        assert isinstance(s, Settings)
        assert s.openai_api_key == "test-key-123"
