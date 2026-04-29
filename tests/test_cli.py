"""Tests for the Startup-Auditor CLI."""

from unittest.mock import patch

from startup_auditor import __version__
from startup_auditor.cli import app
from startup_auditor.exit_codes import EXIT_SUCCESS, EXIT_FAILURE, EXIT_CONFIG_ERROR


def test_cli_help(runner):
    """Test that --help displays correctly."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == EXIT_SUCCESS
    assert "startup-auditor" in result.output
    assert "analyze" in result.output
    assert "report" in result.output
    assert "version" in result.output


def test_cli_version(runner):
    """Test that version command shows version info."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == EXIT_SUCCESS
    assert __version__ in result.output


def test_analyze_command_with_valid_url(runner, sample_url):
    """Test that analyze command accepts valid URL argument."""
    with patch("startup_auditor.cli.Config") as mock_config:
        mock_config.load.return_value.wafer_pass_api_key = "test_key"
        result = runner.invoke(app, ["analyze", sample_url])
        assert result.exit_code == EXIT_SUCCESS
        assert f"Analysis starting for {sample_url}" in result.output


def test_analyze_command_invalid_url(runner):
    """Test that analyze command rejects invalid URLs."""
    result = runner.invoke(app, ["analyze", "not-a-url"])
    assert result.exit_code == EXIT_FAILURE
    assert "Invalid URL" in result.output


def test_analyze_command_missing_api_key(runner, sample_url):
    """Test that analyze command fails with missing API key."""
    with patch("startup_auditor.cli.Config.load") as mock_load:
        from startup_auditor.exceptions import ConfigError
        mock_load.side_effect = ConfigError("Missing WAFER_PASS_API_KEY")
        result = runner.invoke(app, ["analyze", sample_url])
        assert result.exit_code == EXIT_CONFIG_ERROR
        assert "Missing WAFER_PASS_API_KEY" in result.output


def test_analyze_with_options(runner, sample_url):
    """Test analyze command with optional flags."""
    with patch("startup_auditor.cli.Config") as mock_config:
        mock_config.load.return_value.wafer_pass_api_key = "test_key"
        result = runner.invoke(
            app,
            ["analyze", sample_url, "--output", "json", "--verbose"],
        )
        assert result.exit_code == EXIT_SUCCESS
        assert "Verbose: True" in result.output
        assert "Output: json" in result.output


def test_report_command_stub(runner):
    """Test that report command exists (stub implementation)."""
    result = runner.invoke(app, ["report", "test-startup"])
    assert result.exit_code == EXIT_SUCCESS
    assert "not yet implemented" in result.output


def test_config_command_stub(runner):
    """Test that config command exists (stub implementation)."""
    result = runner.invoke(app, ["config"])
    assert result.exit_code == EXIT_SUCCESS
    assert "not yet implemented" in result.output
