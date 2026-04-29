"""Tests for the Startup-Auditor config module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from startup_auditor.config import Config
from startup_auditor.exceptions import ConfigError


class TestConfigLoad:
    """Tests for Config.load() method."""

    def test_load_with_valid_env(self, temp_env_file):
        """Test loading config with valid .env file."""
        with patch("startup_auditor.config.load_dotenv"):
            with patch.dict(os.environ, {"WAFER_PASS_API_KEY": "test_key_123"}):
                config = Config.load(temp_env_file)
                assert config.wafer_pass_api_key == "test_key_123"

    def test_load_missing_api_key(self, tmp_path):
        """Test that missing API key raises ConfigError."""
        fake_env = tmp_path / ".env"
        with patch("startup_auditor.config.load_dotenv"):
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(ConfigError) as exc_info:
                    Config.load(fake_env)
                assert "Missing WAFER_PASS_API_KEY" in str(exc_info.value)

    def test_load_creates_directory(self, tmp_path):
        """Test that load() creates directory if it doesn't exist."""
        nested_path = tmp_path / "nested" / "path" / ".env"
        with patch("startup_auditor.config.load_dotenv"):
            with patch.dict(os.environ, {"WAFER_PASS_API_KEY": "test"}):
                Config.load(nested_path)
                assert nested_path.parent.exists()


class TestConfigEnsureExists:
    """Tests for Config.ensure_config_exists() method."""

    def test_ensure_config_exists_true(self, tmp_path):
        """Test returns True when config exists."""
        # Create a fake .env file in the temp directory
        env_file = tmp_path / ".startup-auditor" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.touch()

        with patch("startup_auditor.config.Path.home") as mock_home:
            mock_home.return_value = tmp_path
            assert Config.ensure_config_exists() is True

    def test_ensure_config_exists_false(self, tmp_path):
        """Test returns False when config doesn't exist."""
        with patch("startup_auditor.config.Path.home") as mock_home:
            mock_home.return_value = tmp_path
            assert Config.ensure_config_exists() is False


class TestConfigCreateTemplate:
    """Tests for Config.create_template() method."""

    def test_create_template(self, tmp_path):
        """Test creating template .env file."""
        template_path = tmp_path / ".env.example"
        result_path = Config.create_template(template_path)
        assert result_path.exists()
        content = result_path.read_text()
        assert "WAFER_PASS_API_KEY" in content
        assert "your_key_here" in content


class TestConfigDataclass:
    """Tests for Config dataclass defaults."""

    def test_default_values(self):
        """Test Config default values."""
        config = Config(wafer_pass_api_key="test_key")
        assert config.verbose is False
        assert config.confidence_threshold == 0.8
        assert config.output_format == "markdown"
        assert config.timeout_minutes == 10
        assert config.rate_limit_delay_ms == 1000

    def test_custom_values(self):
        """Test Config with custom values."""
        config = Config(
            wafer_pass_api_key="test_key",
            verbose=True,
            confidence_threshold=0.9,
            output_format="json",
        )
        assert config.verbose is True
        assert config.confidence_threshold == 0.9
        assert config.output_format == "json"
