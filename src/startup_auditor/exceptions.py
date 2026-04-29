"""Custom exceptions for Startup-Auditor.

Exception hierarchy:
- StartupAuditorError (base)
  - ConfigError (configuration/validation errors, exit code 2)
  - ScraperError (scraping failures, exit code 1)
  - AnalyzerError (analysis failures, exit code 1)

All exceptions include actionable recovery guidance.
"""

from pathlib import Path


class StartupAuditorError(Exception):
    """Base exception for all Startup-Auditor errors.

    Subclasses should provide actionable error messages that include:
    1. What went wrong
    2. How to fix it
    """
    pass


class ConfigError(StartupAuditorError):
    """Configuration or validation error.

    Raised when:
    - API key is missing
    - Config file is invalid
    - Required settings are not provided

    Exit code: 2

    Example:
        try:
            config = Config.load()
        except ConfigError as e:
            print(f"Error: {e}")  # Includes recovery guidance
            sys.exit(EXIT_CONFIG_ERROR)
    """

    def __init__(self, message: str, recovery_hint: str | None = None):
        """Initialize ConfigError with actionable message.

        Args:
            message: Description of the error
            recovery_hint: Optional hint for how to fix the issue
        """
        self.message = message
        self.recovery_hint = recovery_hint if recovery_hint else self._default_recovery_hint()
        super().__init__(f"{message}\n\nRecovery: {self.recovery_hint}")

    def _default_recovery_hint(self) -> str:
        """Provide default recovery guidance for config errors."""
        env_path = Path.home() / ".startup-auditor" / ".env"
        return (
            f"Check your configuration at {env_path}\n"
            f"Ensure WAFER_PASS_API_KEY is set in the .env file.\n"
            f"Run 'cp {env_path}.example {env_path}' to create a template"
        )


class ScraperError(StartupAuditorError):
    """Web scraping error.

    Raised when:
    - URL is unreachable
    - Rate limit exceeded
    - HTML parsing fails

    Exit code: 1

    Example:
        try:
            data = scraper.scrape(url)
        except ScraperError as e:
            logger.error(str(e))  # Includes recovery guidance
            return AnalysisResult(success=False, errors=[e])
    """

    def __init__(self, message: str, recovery_hint: str | None = None):
        """Initialize ScraperError with actionable message.

        Args:
            message: Description of the error
            recovery_hint: Optional hint for how to fix the issue
        """
        self.message = message
        self.recovery_hint = recovery_hint or self._default_recovery_hint()
        super().__init__(f"{message}\n\nRecovery: {self.recovery_hint}")

    def _default_recovery_hint(self) -> str:
        """Provide default recovery guidance for scraper errors."""
        return (
            "Check that the URL is accessible and not blocking bots.\n"
            "Try again with --verbose to see detailed error information.\n"
            "If rate-limited, the tool will automatically retry with backoff."
        )


class AnalyzerError(StartupAuditorError):
    """Analysis error.

    Raised when:
    - LLM call fails
    - Detection engine errors
    - Report generation fails

    Exit code: 1

    Example:
        try:
            findings = analyzer.run(context)
        except AnalyzerError as e:
            # Degraded mode: continue without LLM analysis
            context.add_error(e)
            logger.warning(f"Analysis degraded: {e}")
    """

    def __init__(self, message: str, recovery_hint: str | None = None):
        """Initialize AnalyzerError with actionable message.

        Args:
            message: Description of the error
            recovery_hint: Optional hint for how to fix the issue
        """
        self.message = message
        self.recovery_hint = recovery_hint or self._default_recovery_hint()
        super().__init__(f"{message}\n\nRecovery: {self.recovery_hint}")

    def _default_recovery_hint(self) -> str:
        """Provide default recovery guidance for analyzer errors."""
        return (
            "Analysis will continue in degraded mode without this component.\n"
            "Final report may have reduced confidence scores.\n"
            "Check logs for detailed error information."
        )
