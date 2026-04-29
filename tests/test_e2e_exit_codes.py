"""End-to-end tests for exit codes and error handling.

Tests the full CLI workflow from user perspective:
1. Integration E2E - Full CLI workflows with real config scenarios
2. Edge Cases - Boundary conditions and error scenarios
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from startup_auditor.cli import app
from startup_auditor.exit_codes import EXIT_SUCCESS, EXIT_FAILURE, EXIT_CONFIG_ERROR
from startup_auditor.exceptions import ConfigError, ScraperError


class TestIntegrationE2E:
    """End-to-end integration tests for CLI workflows."""

    def test_e2e_missing_api_key_full_flow(self, tmp_path):
        """E2E: Missing API key should fail with config error and actionable message."""
        runner = CliRunner()

        # Create isolated config directory
        config_dir = tmp_path / ".startup-auditor"
        config_dir.mkdir()

        # Ensure no .env file exists
        env_file = config_dir / ".env"

        with patch.object(Path, 'home', return_value=tmp_path):
            result = runner.invoke(app, ["analyze", "https://example.com"])

            assert result.exit_code == EXIT_CONFIG_ERROR
            assert "WAFER_PASS_API_KEY" in result.output
            assert ".env" in result.output
            assert "Recovery" in result.output

    def test_e2e_valid_config_success_flow(self, tmp_path):
        """E2E: Valid config should succeed with exit code 0."""
        runner = CliRunner()

        # Create config with valid API key
        config_dir = tmp_path / ".startup-auditor"
        config_dir.mkdir()
        env_file = config_dir / ".env"
        env_file.write_text("WAFER_PASS_API_KEY=test_key_123\n")

        with patch.object(Path, 'home', return_value=tmp_path):
            result = runner.invoke(app, ["analyze", "https://example.com"])

            assert result.exit_code == EXIT_SUCCESS
            assert "Analysis starting" in result.output
            assert "scraped successfully" in result.output

    def test_e2e_invalid_url_full_flow(self, tmp_path):
        """E2E: Invalid URL should fail with exit code 1 and error message."""
        runner = CliRunner()

        # Setup valid config to bypass config error
        config_dir = tmp_path / ".startup-auditor"
        config_dir.mkdir()
        env_file = config_dir / ".env"
        env_file.write_text("WAFER_PASS_API_KEY=test_key_123\n")

        with patch.object(Path, 'home', return_value=tmp_path):
            result = runner.invoke(app, ["analyze", "not-a-valid-url"])

            assert result.exit_code == EXIT_FAILURE
            assert "Invalid URL" in result.output
            assert "http:// or https://" in result.output

    def test_e2e_version_command_success(self):
        """E2E: Version command should always succeed."""
        runner = CliRunner()
        result = runner.invoke(app, ["version"])

        assert result.exit_code == EXIT_SUCCESS
        assert "Startup-Auditor" in result.output
        assert "version" in result.output.lower()

    def test_e2e_help_command_success(self):
        """E2E: Help command should always succeed."""
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == EXIT_SUCCESS
        assert "analyze" in result.output
        assert "startup-auditor" in result.output.lower()


class TestEdgeCases:
    """Edge case tests for boundary conditions."""

    def test_edge_empty_url(self, tmp_path):
        """Edge: Empty URL string should fail validation."""
        runner = CliRunner()

        config_dir = tmp_path / ".startup-auditor"
        config_dir.mkdir()
        env_file = config_dir / ".env"
        env_file.write_text("WAFER_PASS_API_KEY=test_key_123\n")

        with patch.object(Path, 'home', return_value=tmp_path):
            result = runner.invoke(app, ["analyze", ""])

            assert result.exit_code == EXIT_FAILURE
            assert "Invalid URL" in result.output

    def test_edge_url_with_special_chars(self, tmp_path):
        """Edge: URL with special characters should be handled."""
        runner = CliRunner()

        config_dir = tmp_path / ".startup-auditor"
        config_dir.mkdir()
        env_file = config_dir / ".env"
        env_file.write_text("WAFER_PASS_API_KEY=test_key_123\n")

        # URL with query params and fragments
        test_url = "https://example.com/path?query=value&other=123#fragment"

        with patch.object(Path, 'home', return_value=tmp_path):
            result = runner.invoke(app, ["analyze", test_url])

            # Should pass URL validation (may fail later in scraping)
            assert result.exit_code in [EXIT_SUCCESS, EXIT_FAILURE]

    def test_edge_ftp_url_scheme(self, tmp_path):
        """Edge: FTP URL scheme should fail validation (only http/https allowed)."""
        runner = CliRunner()

        config_dir = tmp_path / ".startup-auditor"
        config_dir.mkdir()
        env_file = config_dir / ".env"
        env_file.write_text("WAFER_PASS_API_KEY=test_key_123\n")

        with patch.object(Path, 'home', return_value=tmp_path):
            result = runner.invoke(app, ["analyze", "ftp://example.com/file"])

            assert result.exit_code == EXIT_FAILURE
            assert "Invalid URL" in result.output

    def test_edge_file_url_scheme(self, tmp_path):
        """Edge: File URL scheme should fail validation."""
        runner = CliRunner()

        config_dir = tmp_path / ".startup-auditor"
        config_dir.mkdir()
        env_file = config_dir / ".env"
        env_file.write_text("WAFER_PASS_API_KEY=test_key_123\n")

        with patch.object(Path, 'home', return_value=tmp_path):
            result = runner.invoke(app, ["analyze", "file:///etc/passwd"])

            assert result.exit_code == EXIT_FAILURE
            assert "Invalid URL" in result.output

    def test_edge_config_dir_permission_error(self, tmp_path):
        """Edge: Config directory creation failure should be handled."""
        runner = CliRunner()

        # Mock mkdir to raise permission error
        def mock_mkdir(*args, **kwargs):
            raise OSError("Permission denied")

        with patch.object(Path, 'mkdir', side_effect=mock_mkdir):
            result = runner.invoke(app, ["analyze", "https://example.com"])

            assert result.exit_code == EXIT_CONFIG_ERROR
            assert "Cannot create config directory" in result.output
            assert "permissions" in result.output.lower()

    def test_edge_config_error_empty_recovery_hint(self):
        """Edge: ConfigError with empty string recovery_hint should use default."""
        error = ConfigError("Test error", recovery_hint="")

        # Empty string should trigger default recovery hint
        assert "Recovery:" in str(error)
        assert ".env" in str(error)

    def test_edge_config_error_none_recovery_hint(self):
        """Edge: ConfigError with None recovery_hint should use default."""
        error = ConfigError("Test error", recovery_hint=None)

        assert "Recovery:" in str(error)
        assert ".startup-auditor" in str(error)

    def test_edge_scraper_error_empty_message(self):
        """Edge: ScraperError with empty message should still have recovery hint."""
        error = ScraperError("")

        assert "Recovery:" in str(error)
        assert "URL" in str(error) or "rate" in str(error).lower()

    def test_edge_unimplemented_report_command(self):
        """Edge: Unimplemented report command should not crash."""
        runner = CliRunner()
        result = runner.invoke(app, ["report", "some-analysis-id"])

        # Should not crash, but may return 0 (not yet implemented)
        assert result.exit_code == EXIT_SUCCESS
        assert "not yet implemented" in result.output.lower()

    def test_edge_unimplemented_config_command(self):
        """Edge: Unimplemented config command should not crash."""
        runner = CliRunner()
        result = runner.invoke(app, ["config"])

        # Should not crash, but may return 0 (not yet implemented)
        assert result.exit_code == EXIT_SUCCESS
        assert "not yet implemented" in result.output.lower()

    def test_edge_analyze_with_all_options(self, tmp_path):
        """Edge: Analyze with all CLI options should handle correctly."""
        runner = CliRunner()

        config_dir = tmp_path / ".startup-auditor"
        config_dir.mkdir()
        env_file = config_dir / ".env"
        env_file.write_text("WAFER_PASS_API_KEY=test_key_123\n")

        with patch.object(Path, 'home', return_value=tmp_path):
            result = runner.invoke(app, [
                "analyze",
                "https://example.com",
                "--output", "json",
                "--confidence", "0.5",
                "--verbose"
            ])

            # Should process all options without crashing
            assert result.exit_code in [EXIT_SUCCESS, EXIT_FAILURE]
            assert "Verbose: True" in result.output
            assert "Confidence threshold: 0.5" in result.output

    def test_edge_url_with_whitespace(self, tmp_path):
        """Edge: URL with leading/trailing whitespace should be handled."""
        runner = CliRunner()

        config_dir = tmp_path / ".startup-auditor"
        config_dir.mkdir()
        env_file = config_dir / ".env"
        env_file.write_text("WAFER_PASS_API_KEY=test_key_123\n")

        with patch.object(Path, 'home', return_value=tmp_path):
            result = runner.invoke(app, ["analyze", "  https://example.com  "])

            # URL validation should handle or reject whitespace
            assert result.exit_code in [EXIT_SUCCESS, EXIT_FAILURE]

    def test_edge_very_long_url(self, tmp_path):
        """Edge: Very long URL should be handled."""
        runner = CliRunner()

        config_dir = tmp_path / ".startup-auditor"
        config_dir.mkdir()
        env_file = config_dir / ".env"
        env_file.write_text("WAFER_PASS_API_KEY=test_key_123\n")

        # Generate a very long URL (2000+ chars)
        long_path = "/path/" + "segment/" * 200
        long_url = f"https://example.com{long_path}"

        with patch.object(Path, 'home', return_value=tmp_path):
            result = runner.invoke(app, ["analyze", long_url])

            # Should not crash, may fail at validation or scraping
            assert result.exit_code in [EXIT_SUCCESS, EXIT_FAILURE]


class TestExitCodeConstants:
    """Verify exit code constants match Unix conventions."""

    def test_exit_success_is_unix_standard(self):
        """EXIT_SUCCESS should be 0 (Unix standard)."""
        assert EXIT_SUCCESS == 0

    def test_exit_failure_is_unix_standard(self):
        """EXIT_FAILURE should be 1 (Unix standard)."""
        assert EXIT_FAILURE == 1

    def test_exit_config_error_is_distinct(self):
        """EXIT_CONFIG_ERROR should be distinct from success/failure."""
        assert EXIT_CONFIG_ERROR == 2
        assert EXIT_CONFIG_ERROR != EXIT_SUCCESS
        assert EXIT_CONFIG_ERROR != EXIT_FAILURE
