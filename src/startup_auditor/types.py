"""Data types for Startup-Auditor analysis pipeline."""

from dataclasses import dataclass, field


@dataclass
class AnalysisContext:
    """Context passed through the analysis pipeline.

    Attributes:
        url: The startup website URL to analyze
        verbose: Enable verbose logging
        confidence_threshold: Minimum confidence for findings (0.0-1.0)
        output_format: Output format (markdown, json, text)
        findings: List of analysis findings
        errors: List of errors encountered
    """
    url: str
    verbose: bool = False
    confidence_threshold: float = 0.8
    output_format: str = "markdown"
    findings: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    def add_finding(self, finding: dict) -> None:
        """Add a finding to the context."""
        self.findings.append(finding)

    def add_error(self, error: Exception) -> None:
        """Add an error to the context."""
        self.errors.append(error)

    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0


@dataclass
class AnalysisResult:
    """Result from the analysis pipeline.

    Attributes:
        success: Whether analysis completed successfully
        context: The analysis context with findings
        report_path: Path to generated report (if any)
    """
    success: bool
    context: AnalysisContext
    report_path: str | None = None
