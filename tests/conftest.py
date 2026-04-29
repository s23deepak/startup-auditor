"""Pytest fixtures and configuration for Startup-Auditor tests."""

import pytest
from typer.testing import CliRunner

from startup_auditor.cli import app


@pytest.fixture
def runner():
    """Create a Typer CliRunner for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def sample_url():
    """Sample startup URL for testing."""
    return "https://prospectai.com"


@pytest.fixture
def sample_html():
    """Sample HTML content for testing scrapers."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ProspectAI - AI-Powered Prospecting</title>
        <meta name="description" content="AI-powered sales prospecting platform">
    </head>
    <body>
        <h1>ProspectAI</h1>
        <p>Powered by GPT-4 and Claude</p>
        <script src="/app.js"></script>
    </body>
    </html>
    """


@pytest.fixture
def temp_env_file(tmp_path):
    """Create a temporary .env file for testing config loading."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "WAFER_PASS_API_KEY=test_key_123\n"
        "PLAYWRIGHT_BROWSERS_PATH=/tmp/browsers\n"
        "LOG_LEVEL=DEBUG\n"
    )
    return env_file
