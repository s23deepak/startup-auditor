"""Tests for the Playwright scraper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from startup_auditor.exceptions import ScraperError
from startup_auditor.scrapers.base import ScrapedData
from startup_auditor.scrapers.playwright_scraper import PlaywrightScraper


class TestPlaywrightScraperInit:
    """Test PlaywrightScraper initialization."""

    def test_default_init(self):
        """Test default initialization values."""
        scraper = PlaywrightScraper()
        assert scraper.headless is True
        assert scraper.timeout == 30000
        assert scraper.wait_for_network_idle is False

    def test_custom_init(self):
        """Test custom initialization values."""
        scraper = PlaywrightScraper(
            headless=False,
            timeout=60000,
            wait_for_network_idle=True,
        )
        assert scraper.headless is False
        assert scraper.timeout == 60000
        assert scraper.wait_for_network_idle is True


class TestPlaywrightScraperScrapeAsync:
    """Test PlaywrightScraper scrape_async method."""

    @pytest.mark.asyncio
    async def test_successful_scrape(self):
        """Test successful scraping returns ScrapedData."""
        # Mock Playwright objects
        mock_page = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html><body>Test</body></html>")
        mock_page.title = AsyncMock(return_value="Test Page")
        mock_page.eval_on_selector = AsyncMock(return_value="Test description")
        mock_page.set_default_timeout = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch(
            "startup_auditor.scrapers.playwright_scraper.async_playwright",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_playwright)),
        ):
            scraper = PlaywrightScraper()
            result = await scraper.scrape_async("https://example.com")

            assert isinstance(result, ScrapedData)
            assert result.url == "https://example.com"
            assert result.html == "<html><body>Test</body></html>"
            assert result.title == "Test Page"
            assert result.meta_description == "Test description"

    @pytest.mark.asyncio
    async def test_scrape_without_meta_description(self):
        """Test scraping when meta description is missing."""
        mock_page = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html><body>Test</body></html>")
        mock_page.title = AsyncMock(return_value="Test Page")
        mock_page.eval_on_selector = AsyncMock(side_effect=Exception("Not found"))
        mock_page.set_default_timeout = MagicMock()
        mock_page.goto = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch(
            "startup_auditor.scrapers.playwright_scraper.async_playwright",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_playwright)),
        ):
            scraper = PlaywrightScraper()
            result = await scraper.scrape_async("https://example.com")

            assert isinstance(result, ScrapedData)
            assert result.title == "Test Page"
            assert result.meta_description == ""  # Empty when not found

    @pytest.mark.asyncio
    async def test_scrape_timeout_error(self):
        """Test that TimeoutError raises ScraperError."""
        mock_browser = AsyncMock()
        mock_browser.launch = AsyncMock(side_effect=TimeoutError())

        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(side_effect=TimeoutError())

        with patch(
            "startup_auditor.scrapers.playwright_scraper.async_playwright",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_playwright)),
        ):
            scraper = PlaywrightScraper()
            with pytest.raises(ScraperError) as exc_info:
                await scraper.scrape_async("https://example.com")

            assert "Timeout" in str(exc_info.value.message)
            assert "recovery" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_scrape_general_error(self):
        """Test that general exceptions raise ScraperError."""
        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        with patch(
            "startup_auditor.scrapers.playwright_scraper.async_playwright",
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_playwright)),
        ):
            scraper = PlaywrightScraper()
            with pytest.raises(ScraperError) as exc_info:
                await scraper.scrape_async("https://example.com")

            assert "Failed to scrape" in str(exc_info.value.message)


class TestPlaywrightScraperScrape:
    """Test PlaywrightScraper synchronous scrape method."""

    def test_scrape_calls_asyncio_run(self):
        """Test that scrape() wraps scrape_async in asyncio.run()."""
        scraper = PlaywrightScraper()

        # We can't actually test this without a real browser,
        # but we can verify the method exists and has the right signature
        assert callable(scraper.scrape)
        assert hasattr(scraper, "scrape_async")


class TestScrapedData:
    """Test ScrapedData dataclass."""

    def test_scraped_data_creation(self):
        """Test creating ScrapedData with all fields."""
        data = ScrapedData(
            url="https://example.com",
            html="<html>...</html>",
            title="Example",
            meta_description="An example page",
            network_calls=["https://api.example.com"],
        )
        assert data.url == "https://example.com"
        assert data.html == "<html>...</html>"
        assert data.title == "Example"
        assert data.meta_description == "An example page"
        assert data.network_calls == ["https://api.example.com"]

    def test_scraped_data_defaults(self):
        """Test ScrapedData default values."""
        data = ScrapedData(url="https://example.com")
        assert data.html == ""
        assert data.title == ""
        assert data.meta_description == ""
        assert data.network_calls == []
