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
        confidence: Overall confidence score (0.0-1.0), reduced on errors
    """
    url: str
    verbose: bool = False
    confidence_threshold: float = 0.8
    output_format: str = "markdown"
    findings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    confidence: float = 1.0

    def add_finding(self, finding: dict) -> None:
        """Add a finding to the context."""
        self.findings.append(finding)

    def add_error(self, error: Exception) -> None:
        """Add an error to the context."""
        self.errors.append(error)

    def reduce_confidence(self, amount: float, reason: str = "") -> None:
        """Reduce confidence score by a specified amount.

        Args:
            amount: Amount to reduce (0.0-1.0)
            reason: Optional reason for the reduction
        """
        self.confidence = max(0.0, self.confidence - amount)
        if self.verbose and reason:
            print(f"Confidence reduced by {amount:.1f}: {reason}")

    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0

    @property
    def is_below_threshold(self) -> bool:
        """Check if confidence is below threshold."""
        return self.confidence < self.confidence_threshold


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
