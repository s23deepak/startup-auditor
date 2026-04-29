"""Base scraper interface for Startup-Auditor.

This module defines the interface that all scrapers must implement.
MVP uses a stub implementation - full Playwright scraper in Story 2.1.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from startup_auditor.exceptions import ScraperError


@dataclass
class ScrapedData:
    """Data returned from scraping a website.

    Attributes:
        url: The URL that was scraped
        html: Raw HTML content
        title: Page title
        meta_description: Meta description if present
        network_calls: List of network calls detected (future)
    """
    url: str
    html: str = ""
    title: str = ""
    meta_description: str = ""
    network_calls: list = None

    def __post_init__(self):
        if self.network_calls is None:
            self.network_calls = []


class BaseScraper(ABC):
    """Abstract base class for all scrapers.

    Subclasses must implement the scrape() method.

    Raises:
        ScraperError: If scraping fails
    """

    @abstractmethod
    def scrape(self, url: str) -> ScrapedData:
        """Scrape a website and return extracted data.

        Args:
            url: The URL to scrape

        Returns:
            ScrapedData containing HTML and metadata
        """
        pass


class StubScraper(BaseScraper):
    """Stub scraper for testing and MVP.

    Returns mock data instead of actually scraping.
    Use this until Playwright scraper is implemented in Story 2.1.
    """

    def scrape(self, url: str) -> ScrapedData:
        """Return stubbed scraped data.

        Args:
            url: The URL to "scrape"

        Returns:
            ScrapedData with placeholder content
        """
        return ScrapedData(
            url=url,
            html=f"<!DOCTYPE html><html><body>Stub content for {url}</body></html>",
            title="Stub Page",
            meta_description="This is a stub for MVP testing",
        )
