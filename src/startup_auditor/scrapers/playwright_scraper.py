"""Playwright-based web scraper for Startup-Auditor.

Uses Playwright to scrape dynamic JavaScript-heavy websites.
Supports headless browsing, network call interception, and graceful error handling.
"""

import asyncio
from html.parser import HTMLParser
from typing import Any

from playwright.async_api import async_playwright

from startup_auditor.exceptions import ScraperError
from startup_auditor.scrapers.base import BaseScraper, ScrapedData


class MetaDescriptionParser(HTMLParser):
    """HTML parser to extract meta description."""

    def __init__(self) -> None:
        super().__init__()
        self.description: str = ""
        self._in_meta = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "meta":
            attr_dict = {k: v for k, v in attrs}
            if attr_dict.get("name") == "description":
                self.description = attr_dict.get("content", "")


class PlaywrightScraper(BaseScraper):
    """Playwright-based scraper for dynamic websites.

    Features:
    - Headless browser automation
    - JavaScript rendering support
    - Network call interception (future)
    - Graceful error handling

    Usage:
        scraper = PlaywrightScraper()
        data = await scraper.scrape_async("https://example.com")
    """

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,
        wait_for_network_idle: bool = False,
    ) -> None:
        """Initialize Playwright scraper.

        Args:
            headless: Run browser in headless mode
            timeout: Page load timeout in milliseconds
            wait_for_network_idle: Wait for network to idle (slower but more complete)
        """
        self.headless = headless
        self.timeout = timeout
        self.wait_for_network_idle = wait_for_network_idle

    async def scrape_async(self, url: str) -> ScrapedData:
        """Scrape a website asynchronously.

        Args:
            url: The URL to scrape

        Returns:
            ScrapedData containing HTML, title, and metadata

        Raises:
            ScraperError: If scraping fails
        """
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=self.headless)
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                )
                page = await context.new_page()

                # Set timeout
                page.set_default_timeout(self.timeout)

                # Navigate to page
                await page.goto(url, wait_until="domcontentloaded")

                # Wait for network idle if requested
                if self.wait_for_network_idle:
                    await page.wait_for_load_state("networkidle")

                # Extract content
                html = await page.content()
                title = await page.title()

                # Extract meta description
                meta_description = await self._extract_meta_description(page)

                await browser.close()

                return ScrapedData(
                    url=url,
                    html=html,
                    title=title,
                    meta_description=meta_description,
                )

        except TimeoutError as e:
            raise ScraperError(
                f"Timeout while loading {url}",
                recovery_hint=(
                    "The website may be slow or blocking automated requests.\n"
                    "Try increasing the timeout or check if the URL is accessible."
                ),
            ) from e
        except Exception as e:
            raise ScraperError(
                f"Failed to scrape {url}: {str(e)}",
                recovery_hint=(
                    "Check that the URL is valid and accessible.\n"
                    "Some websites block automated browsers - try a different URL."
                ),
            ) from e

    async def _extract_meta_description(self, page: Any) -> str:
        """Extract meta description from page.

        Args:
            page: Playwright page object

        Returns:
            Meta description content or empty string
        """
        try:
            description = await page.eval_on_selector(
                'meta[name="description"]',
                "element => element.getAttribute('content')",
            )
            return description or ""
        except Exception:
            # Meta description not found
            return ""

    def scrape(self, url: str) -> ScrapedData:
        """Scrape a website (synchronous wrapper).

        Args:
            url: The URL to scrape

        Returns:
            ScrapedData containing HTML, title, and metadata

        Raises:
            ScraperError: If scraping fails
        """
        return asyncio.run(self.scrape_async(url))
