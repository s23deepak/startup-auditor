"""Web scraping module for Startup-Auditor.

Provides scrapers for extracting website content:
- StubScraper: For testing and MVP
- PlaywrightScraper: Full browser automation for dynamic sites
- RateLimiter: Rate limiting with exponential backoff
- NetworkInterceptor: Network call detection and classification
"""

from startup_auditor.scrapers.base import BaseScraper, ScrapedData, StubScraper
from startup_auditor.scrapers.playwright_scraper import PlaywrightScraper
from startup_auditor.scrapers.rate_limiter import RateLimiter, RetryResult
from startup_auditor.scrapers.network_interceptor import NetworkInterceptor, NetworkCall, detect_wafer_pass

__all__ = [
    "BaseScraper",
    "ScrapedData",
    "StubScraper",
    "PlaywrightScraper",
    "RateLimiter",
    "RetryResult",
    "NetworkInterceptor",
    "NetworkCall",
    "detect_wafer_pass",
]
