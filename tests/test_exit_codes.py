"""Tests for exit codes and error handling.

Verifies that:
1. Exit codes are consistent (0=success, 1=failure, 2=config error)
2. Error messages are actionable (include recovery guidance)
3. Exceptions are properly raised and caught
"""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from startup_auditor.cli import app
from startup_auditor.exit_codes import EXIT_SUCCESS, EXIT_FAILURE, EXIT_CONFIG_ERROR
from startup_auditor.exceptions import ConfigError, ScraperError, AnalyzerError


class TestExitCodes:
    """Test exit code constants."""

    def test_exit_success_is_zero(self):
        """EXIT_SUCCESS should be 0 (Unix convention)."""
        assert EXIT_SUCCESS == 0

    def test_exit_failure_is_one(self):
        """EXIT_FAILURE should be 1 (Unix convention)."""
        assert EXIT_FAILURE == 1

    def test_exit_config_error_is_two(self):
        """EXIT_CONFIG_ERROR should be 2 (config-specific)."""
        assert EXIT_CONFIG_ERROR == 2


class TestExceptions:
    """Test exception classes and their error messages."""

    def test_config_error_has_recovery_hint(self):
        """ConfigError should include recovery guidance."""
        error = ConfigError("Missing API key")
        assert "Recovery:" in str(error)
        assert ".startup-auditor" in str(error)

    def test_config_error_custom_recovery(self):
        """ConfigError should accept custom recovery hints."""
        custom_hint = "Custom fix instructions"
        error = ConfigError("Config error", recovery_hint=custom_hint)
        assert custom_hint in str(error)

    def test_scraper_error_has_recovery_hint(self):
        """ScraperError should include recovery guidance."""
        error = ScraperError("Failed to scrape")
        assert "Recovery:" in str(error)
        assert "URL" in str(error) or "rate" in str(error).lower()

    def test_scraper_error_custom_recovery(self):
        """ScraperError should accept custom recovery hints."""
        custom_hint = "Custom fix instructions"
        error = ScraperError("Scrape failed", recovery_hint=custom_hint)
        assert custom_hint in str(error)

    def test_analyzer_error_has_recovery_hint(self):
        """AnalyzerError should include recovery guidance."""
        error = AnalyzerError("LLM call failed")
        assert "Recovery:" in str(error)
        assert "degraded mode" in str(error).lower()

    def test_analyzer_error_custom_recovery(self):
        """AnalyzerError should accept custom recovery hints."""
        custom_hint = "Custom fix instructions"
        error = AnalyzerError("Analysis failed", recovery_hint=custom_hint)
        assert custom_hint in str(error)

    def test_exception_hierarchy(self):
        """All custom exceptions should inherit from StartupAuditorError."""
        from startup_auditor.exceptions import StartupAuditorError

        assert issubclass(ConfigError, StartupAuditorError)
        assert issubclass(ScraperError, StartupAuditorError)
        assert issubclass(AnalyzerError, StartupAuditorError)


class TestCLIExitCodes:
    """Test CLI commands return correct exit codes."""

    def test_version_returns_success(self):
        """Version command should return EXIT_SUCCESS."""
        runner = CliRunner()
        result = runner.invoke(app, ["version"])
        assert result.exit_code == EXIT_SUCCESS

    def test_analyze_invalid_url_returns_failure(self):
        """Analyze with invalid URL should return EXIT_FAILURE."""
        runner = CliRunner()
        result = runner.invoke(app, ["analyze", "not-a-url"])
        assert result.exit_code == EXIT_FAILURE

    def test_analyze_missing_api_key_returns_config_error(self):
        """Analyze with missing API key should return EXIT_CONFIG_ERROR."""
        runner = CliRunner()
        with patch("startup_auditor.cli.Config.load") as mock_load:
            mock_load.side_effect = ConfigError(
                "Missing WAFER_PASS_API_KEY",
                recovery_hint="Set your API key"
            )
            result = runner.invoke(app, ["analyze", "https://example.com"])
            assert result.exit_code == EXIT_CONFIG_ERROR

    def test_analyze_success_with_mocked_config(self):
        """Analyze with valid config should return EXIT_SUCCESS."""
        runner = CliRunner()
        with patch("startup_auditor.cli.Config") as mock_config_class:
            mock_config_class.load.return_value.wafer_pass_api_key = "test_key"
            result = runner.invoke(app, ["analyze", "https://example.com"])
            assert result.exit_code == EXIT_SUCCESS

    def test_help_returns_success(self):
        """Help command should return EXIT_SUCCESS."""
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == EXIT_SUCCESS


class TestErrorMessageContent:
    """Test that error messages contain actionable information."""

    def test_config_error_mentions_env_file(self):
        """ConfigError should mention .env file location."""
        error = ConfigError("Missing key")
        assert ".env" in str(error)

    def test_config_error_mentions_api_key(self):
        """ConfigError should mention WAFER_PASS_API_KEY."""
        error = ConfigError("Missing key")
        assert "WAFER_PASS_API_KEY" in str(error)

    def test_scraper_error_mentions_url_or_retry(self):
        """ScraperError should mention URL or retry behavior."""
        error = ScraperError("Scrape failed")
        error_str = str(error).lower()
        assert "url" in error_str or "retry" in error_str or "rate" in error_str

    def test_analyzer_error_mentions_degraded_mode(self):
        """AnalyzerError should mention degraded mode."""
        error = AnalyzerError("Analysis failed")
        assert "degraded" in str(error).lower()
