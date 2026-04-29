"""Playwright-based web scraper for Startup-Auditor.

Uses Playwright to scrape dynamic JavaScript-heavy websites.
Supports headless browsing, network call interception, and graceful error handling.
Includes rate limiting with exponential backoff and retry logic.
"""

import asyncio
from html.parser import HTMLParser
from typing import Any

from playwright.async_api import async_playwright, Response

from startup_auditor.exceptions import ScraperError
from startup_auditor.scrapers.base import BaseScraper, ScrapedData
from startup_auditor.scrapers.rate_limiter import RateLimiter, RetryResult
from startup_auditor.scrapers.network_interceptor import NetworkInterceptor, detect_wafer_pass


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
    - Rate limiting with exponential backoff
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
        max_retries: int = 3,
        verbose: bool = False,
    ) -> None:
        """Initialize Playwright scraper.

        Args:
            headless: Run browser in headless mode
            timeout: Page load timeout in milliseconds
            wait_for_network_idle: Wait for network to idle (slower but more complete)
            max_retries: Maximum retry attempts for rate limiting (default: 3)
            verbose: Enable verbose logging for retry attempts
        """
        self.headless = headless
        self.timeout = timeout
        self.wait_for_network_idle = wait_for_network_idle
        self.max_retries = max_retries
        self.verbose = verbose
        self.rate_limiter = RateLimiter(max_retries=max_retries)

    async def scrape_async(self, url: str) -> ScrapedData:
        """Scrape a website asynchronously with retry logic.

        Args:
            url: The URL to scrape

        Returns:
            ScrapedData containing HTML, title, and metadata

        Raises:
            ScraperError: If scraping fails after all retries
        """

        async def _scrape_once() -> ScrapedData:
            """Inner scrape function for retry wrapper."""
            browser = None
            network_interceptor = NetworkInterceptor()
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

                    # Set up network interception
                    page.on("request", network_interceptor.on_request)
                    page.on("response", network_interceptor.on_response)

                    # Navigate to page
                    response = await page.goto(url, wait_until="domcontentloaded")

                    # Check for None response (navigation failure)
                    if response is None:
                        raise ScraperError(
                            f"No response received for {url}",
                            recovery_hint="Check if the URL is accessible and not blocking automated browsers.",
                        )

                    # Check for 429 rate limit - include status code for retry detection
                    if response.status == 429:
                        retry_after = response.headers.get("retry-after")
                        raise ScraperError(
                            f"Rate limited (429). Retry-After: {retry_after}" if retry_after else "Rate limited (429).",
                            recovery_hint="Will retry with exponential backoff.",
                            last_response_status=429,
                        )

                    # Wait for network idle if requested
                    if self.wait_for_network_idle:
                        await page.wait_for_load_state("networkidle")

                    # Finalize network interception (deduplicate and classify)
                    network_interceptor.finalize()

                    # Extract content
                    html = await page.content()
                    title = await page.title()

                    # Extract meta description
                    meta_description = await self._extract_meta_description(page)

                    # Get network calls
                    network_calls = [call.url for call in network_interceptor.get_network_calls()]

                    return ScrapedData(
                        url=url,
                        html=html,
                        title=title,
                        meta_description=meta_description,
                        network_calls=network_calls,
                    )
            finally:
                # Ensure browser is always closed, even on error
                if browser is not None:
                    await browser.close()

        def _on_retry(attempt: int, error: Exception, delay: float) -> None:
            """Callback for retry events."""
            if self.verbose:
                print(f"Retry {attempt + 1}/{self.max_retries}: {type(error).__name__} - Waiting {delay:.1f}s")

        # Execute with retry logic - pass status code for 429 detection
        result = await self.rate_limiter.execute_with_retry(
            _scrape_once,
            on_retry=_on_retry,
        )

        # Execute with retry logic
        result = await self.rate_limiter.execute_with_retry(
            _scrape_once,
            on_retry=_on_retry,
        )

        if result.success:
            # Log retry count unconditionally (AC5 requirement)
            if result.retries_attempted > 0:
                print(f"Scrape succeeded after {result.retries_attempted} retries")
            return result.result
        else:
            # All retries exhausted - log unconditionally (AC2 requirement)
            print(f"Rate limited. Falling back to external sources.")

            # Check if it was a rate limiting issue - fix operator precedence
            if result.error and ("429" in str(result.error) or isinstance(result.error, TimeoutError)):
                raise ScraperError(
                    f"Failed to scrape {url} after {result.retries_attempted} retries: {str(result.error)}",
                    recovery_hint=(
                        "Rate limited. Falling back to external sources.\n"
                        "Consider reducing request frequency or using cached data."
                    ),
                    max_retries=self.max_retries,
                    retries_attempted=result.retries_attempted,
                    last_response_status=429 if "429" in str(result.error) else None,
                ) from result.error

            # General scrape failure - include retry metadata
            raise ScraperError(
                f"Failed to scrape {url} after {result.retries_attempted} retries: {str(result.error)}",
                recovery_hint=(
                    "Check that the URL is valid and accessible.\n"
                    "Some websites block automated browsers - try a different URL."
                ),
                max_retries=self.max_retries,
                retries_attempted=result.retries_attempted,
            ) from result.error

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
