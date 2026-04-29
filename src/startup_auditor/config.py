"""Configuration loading for Startup-Auditor.

MVP uses 2-layer config:
1. .env file for secrets (WAFER_PASS_API_KEY)
2. Hardcoded defaults for runtime options

YAML config deferred to Phase 2.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from startup_auditor.exceptions import ConfigError


@dataclass
class Config:
    """Application configuration.

    Attributes:
        wafer_pass_api_key: Wafer Pass LLM API key
        verbose: Enable verbose logging
        confidence_threshold: Minimum confidence for findings (0.0-1.0)
        output_format: Default output format
        timeout_minutes: Analysis timeout
        rate_limit_delay_ms: Delay between requests
    """
    wafer_pass_api_key: str
    verbose: bool = False
    confidence_threshold: float = 0.8
    output_format: str = "markdown"
    timeout_minutes: int = 10
    rate_limit_delay_ms: int = 1000

    @classmethod
    def load(cls, env_path: Path | None = None) -> "Config":
        """Load configuration from .env file.

        Args:
            env_path: Optional path to .env file. If not provided,
                     uses ~/.startup-auditor/.env

        Returns:
            Config object with loaded settings

        Raises:
            ConfigError: If API key is missing or config is invalid
        """
        if env_path is None:
            env_path = Path.home() / ".startup-auditor" / ".env"

        # Create directory if it doesn't exist
        try:
            env_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise ConfigError(
                f"Cannot create config directory: {e}",
                recovery_hint="Check that you have write permissions for your home directory"
            )

        # Load .env file if it exists
        if env_path.exists():
            load_dotenv(env_path)

        # Get API key from environment
        api_key = os.getenv("WAFER_PASS_API_KEY")

        if not api_key:
            raise ConfigError(
                f"Missing WAFER_PASS_API_KEY. Set in {env_path}",
                recovery_hint=(
                    f"1. Copy the template: cp {env_path}.example {env_path}\n"
                    f"2. Edit {env_path} and add your WAFER_PASS_API_KEY\n"
                    f"3. Get your key from https://docs.wafer.ai/wafer-pass"
                )
            )

        return cls(
            wafer_pass_api_key=api_key,
            verbose=os.getenv("LOG_LEVEL", "").upper() == "DEBUG",
        )

    @classmethod
    def ensure_config_exists(cls) -> bool:
        """Check if config file exists.

        Returns:
            True if config exists, False otherwise
        """
        env_path = Path.home() / ".startup-auditor" / ".env"
        return env_path.exists()

    @classmethod
    def create_template(cls, output_path: Path | None = None) -> Path:
        """Create a template .env file.

        Args:
            output_path: Optional path for the template file.
                        Defaults to ~/.startup-auditor/.env.example

        Returns:
            Path to created template file
        """
        if output_path is None:
            output_path = Path.home() / ".startup-auditor" / ".env.example"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        template = """# Startup-Auditor Environment Configuration
# Copy this file to .env and fill in your actual values

# Wafer Pass LLM API Key (required)
WAFER_PASS_API_KEY=your_key_here

# Log Level (optional)
# Options: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO
"""
        output_path.write_text(template)
        return output_path
