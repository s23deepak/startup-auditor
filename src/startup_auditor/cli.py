"""CLI entry point for Startup-Auditor.

Uses Typer for modern CLI with type hints, auto-completion, and help text.
"""

import typer
from rich.console import Console

from startup_auditor import __version__
from startup_auditor.exit_codes import EXIT_SUCCESS, EXIT_FAILURE, EXIT_CONFIG_ERROR
from startup_auditor.types import AnalysisContext, AnalysisResult
from startup_auditor.scrapers.base import StubScraper
from startup_auditor.exceptions import ScraperError, ConfigError
from startup_auditor.config import Config

app = typer.Typer(
    name="startup-auditor",
    help="Automated startup analysis for AI/ML engineers targeting AI-first startups.",
    add_completion=False,
)
console = Console()


def _validate_url(url: str) -> bool:
    """Validate that a URL is well-formed.

    Args:
        url: URL string to validate

    Returns:
        True if valid URL, False otherwise
    """
    return url.startswith(("http://", "https://"))


@app.command()
def analyze(
    url: str = typer.Argument(..., help="Startup website URL to analyze"),
    output: str = typer.Option(
        "markdown",
        "--output",
        "-o",
        help="Output format: markdown (default), json, text",
    ),
    confidence: float = typer.Option(
        0.8,
        "--confidence",
        "-c",
        help="Minimum confidence threshold (default: 0.8)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """Analyze a startup website and generate a gap analysis report.

    Example:
        startup-auditor analyze https://prospectai.com
        startup-auditor analyze https://example.com --output=json --verbose
    """
    # Validate URL
    if not _validate_url(url):
        console.print(f"[red]Error: Invalid URL '{url}'. URL must start with http:// or https://[/red]")
        raise typer.Exit(code=EXIT_FAILURE)

    # Load config (validates API key)
    try:
        config = Config.load()
        if verbose:
            console.print("[dim]Configuration loaded successfully[/dim]")
    except ConfigError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR)
    except Exception as e:
        console.print(f"[red]Unexpected error loading config: {e}[/red]")
        raise typer.Exit(code=EXIT_FAILURE)

    # Create analysis context
    ctx = AnalysisContext(
        url=url,
        verbose=verbose,
        confidence_threshold=confidence,
        output_format=output,
    )

    console.print(f"[bold blue]Analysis starting for {url}...[/bold blue]")

    # Run stub scraper (Story 2.1 will implement real scraper)
    try:
        scraper = StubScraper()
        scraped_data = scraper.scrape(url)
        ctx.add_finding({
            "type": "scrape",
            "status": "success",
            "url": url,
        })
        console.print("[green]Website scraped successfully (stub mode)[/green]")
    except ScraperError as e:
        ctx.add_error(e)
        console.print(f"[red]Scraping failed: {e}[/red]")
        raise typer.Exit(code=EXIT_FAILURE)

    console.print(f"[dim]Verbose: {verbose}, Confidence threshold: {confidence}, Output: {output}[/dim]")
    console.print("[yellow]Full analysis pipeline coming in subsequent stories.[/yellow]")

    raise typer.Exit(EXIT_SUCCESS)


@app.command()
def report(
    analysis_id: str = typer.Argument(..., help="Analysis ID or startup name"),
) -> None:
    """View or regenerate a previously generated report."""
    console.print(f"[yellow]Report command not yet implemented. Analysis ID: {analysis_id}[/yellow]")


@app.command(name="config")
def config_command() -> None:
    """Configure API keys and analysis thresholds."""
    console.print("[yellow]Config command not yet implemented.[/yellow]")


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"[bold]Startup-Auditor[/bold] version [green]{__version__}[/green]")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    app()
