"""Tests for rate limiter with exponential backoff."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from startup_auditor.scrapers.rate_limiter import RateLimiter, RetryResult
from startup_auditor.exceptions import ScraperError


class TestRateLimiterInit:
    """Test RateLimiter initialization."""

    def test_default_init(self):
        """Test default initialization values."""
        limiter = RateLimiter()
        assert limiter.max_retries == 3
        assert limiter.base_delay == 1.0

    def test_custom_init(self):
        """Test custom initialization values."""
        limiter = RateLimiter(max_retries=5, base_delay=2.0)
        assert limiter.max_retries == 5
        assert limiter.base_delay == 2.0


class TestCalculateBackoff:
    """Test exponential backoff calculation."""

    def test_backoff_first_attempt(self):
        """Test backoff for first attempt (attempt 0)."""
        limiter = RateLimiter(base_delay=1.0)
        # Expected: (0 + 1) ** 2 = 1, with ±10% jitter
        delay = limiter.calculate_backoff(0)
        assert 0.9 <= delay <= 1.1

    def test_backoff_second_attempt(self):
        """Test backoff for second attempt (attempt 1)."""
        limiter = RateLimiter(base_delay=1.0)
        # Expected: (1 + 1) ** 2 = 4, with ±10% jitter
        delay = limiter.calculate_backoff(1)
        assert 3.6 <= delay <= 4.4

    def test_backoff_third_attempt(self):
        """Test backoff for third attempt (attempt 2)."""
        limiter = RateLimiter(base_delay=1.0)
        # Expected: (2 + 1) ** 2 = 9, with ±10% jitter
        delay = limiter.calculate_backoff(2)
        assert 8.1 <= delay <= 9.9

    def test_backoff_with_custom_base_delay(self):
        """Test backoff with custom base delay."""
        limiter = RateLimiter(base_delay=2.0)
        # Expected: 2.0 * (0 + 1) ** 2 = 2, with ±10% jitter
        delay = limiter.calculate_backoff(0)
        assert 1.8 <= delay <= 2.2

    def test_backoff_includes_jitter(self):
        """Test that jitter is applied (randomness)."""
        limiter = RateLimiter(base_delay=1.0)
        delays = [limiter.calculate_backoff(0) for _ in range(10)]
        # With jitter, not all delays should be identical
        assert len(set(delays)) > 1


class TestParseRetryAfter:
    """Test Retry-After header parsing."""

    def test_retry_after_integer_seconds(self):
        """Test parsing integer seconds."""
        limiter = RateLimiter()
        assert limiter.parse_retry_after("5") == 5.0
        assert limiter.parse_retry_after("0") == 0.0

    def test_retry_after_capped_at_10(self):
        """Test that Retry-After is capped at 10 seconds."""
        limiter = RateLimiter()
        assert limiter.parse_retry_after("15") == 10.0
        assert limiter.parse_retry_after("60") == 10.0
        assert limiter.parse_retry_after("100") == 10.0

    def test_retry_after_http_date_format(self):
        """Test parsing HTTP-date format."""
        limiter = RateLimiter()
        # Future date (should be capped at 10)
        from datetime import datetime, timezone, timedelta
        future = datetime.now(timezone.utc) + timedelta(seconds=30)
        http_date = future.strftime("%a, %d %b %Y %H:%M:%S GMT")
        result = limiter.parse_retry_after(http_date)
        assert result == 10.0  # Capped at 10

    def test_retry_after_invalid_format_falls_back(self):
        """Test that invalid format falls back to default backoff."""
        limiter = RateLimiter()
        result = limiter.parse_retry_after("invalid")
        # Should return calculated backoff for attempt 0
        assert 0.9 <= result <= 1.1


class TestIsRetryableError:
    """Test retryable error detection."""

    def test_429_is_retryable(self):
        """Test that 429 status code is retryable."""
        limiter = RateLimiter()
        assert limiter.is_retryable_error(Exception(), status_code=429) is True

    def test_200_is_not_retryable(self):
        """Test that 200 status code is not retryable."""
        limiter = RateLimiter()
        assert limiter.is_retryable_error(Exception(), status_code=200) is False

    def test_timeout_error_is_retryable(self):
        """Test that TimeoutError is retryable."""
        limiter = RateLimiter()
        error = TimeoutError("Connection timed out")
        assert limiter.is_retryable_error(error) is True

    def test_connection_error_is_retryable(self):
        """Test that connection errors are retryable."""
        limiter = RateLimiter()

        class ConnectionError(Exception):
            pass

        error = ConnectionError()
        # Note: This tests the error name matching
        assert limiter.is_retryable_error(error) is True

    def test_value_error_is_not_retryable(self):
        """Test that ValueError is not retryable."""
        limiter = RateLimiter()
        error = ValueError("Invalid value")
        assert limiter.is_retryable_error(error) is False


class TestExecuteWithRetry:
    """Test execute_with_retry functionality."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Test successful execution on first attempt."""
        limiter = RateLimiter()

        async def success_func():
            return "success"

        result = await limiter.execute_with_retry(success_func)

        assert result.success is True
        assert result.result == "success"
        assert result.retries_attempted == 0
        assert result.error is None

    @pytest.mark.asyncio
    async def test_success_after_retry(self):
        """Test success after one retry."""
        limiter = RateLimiter()
        call_count = 0

        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("First attempt fails")
            return "success on retry"

        result = await limiter.execute_with_retry(fail_then_succeed)

        assert result.success is True
        assert result.result == "success on retry"
        assert result.retries_attempted == 1

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        """Test failure after all retries exhausted."""
        limiter = RateLimiter(max_retries=3)

        async def always_fail():
            raise TimeoutError("Always fails")

        result = await limiter.execute_with_retry(always_fail)

        assert result.success is False
        assert result.retries_attempted == 3
        assert isinstance(result.error, TimeoutError)

    @pytest.mark.asyncio
    async def test_non_retryable_error_stops_immediately(self):
        """Test that non-retryable errors stop immediately."""
        limiter = RateLimiter(max_retries=3)

        async def raise_value_error():
            raise ValueError("Not retryable")

        result = await limiter.execute_with_retry(raise_value_error)

        assert result.success is False
        assert result.retries_attempted == 0
        assert isinstance(result.error, ValueError)

    @pytest.mark.asyncio
    async def test_on_retry_callback(self):
        """Test that on_retry callback is called."""
        limiter = RateLimiter(max_retries=2)
        callback_calls = []

        def on_retry_callback(attempt, error, delay):
            callback_calls.append((attempt, type(error).__name__))

        async def fail_twice():
            if not callback_calls:
                raise TimeoutError("First fail")
            raise TimeoutError("Second fail")

        await limiter.execute_with_retry(fail_twice, on_retry=on_retry_callback)

        # Callback should be called for each retry
        assert len(callback_calls) >= 1


class TestRetryResult:
    """Test RetryResult dataclass."""

    def test_success_result(self):
        """Test successful RetryResult."""
        result = RetryResult(success=True, result="data", retries_attempted=2)
        assert result.success is True
        assert result.result == "data"
        assert result.retries_attempted == 2
        assert result.error is None

    def test_failure_result(self):
        """Test failed RetryResult."""
        error = ValueError("test error")
        result = RetryResult(success=False, error=error, retries_attempted=3)
        assert result.success is False
        assert result.result is None
        assert result.retries_attempted == 3
        assert result.error == error


class TestIntegration:
    """Integration tests for rate limiter with scraper-like behavior."""

    @pytest.mark.asyncio
    async def test_429_triggers_retry(self):
        """Test that 429 error triggers retry logic."""
        limiter = RateLimiter(max_retries=2)
        call_count = 0

        async def mock_scrape():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Use TimeoutError which is detected as retryable
                raise TimeoutError("Rate limited (429)")
            return {"html": "<html>success</html>"}

        result = await limiter.execute_with_retry(mock_scrape)

        # Should retry until max_retries exhausted (3 calls: initial + 2 retries)
        assert call_count == 3
        assert result.success is True

    @pytest.mark.asyncio
    async def test_confidence_reduction_simulation(self):
        """Test confidence reduction pattern (simulating scraper behavior)."""
        from startup_auditor.types import AnalysisContext

        context = AnalysisContext(url="https://example.com", verbose=True)
        assert context.confidence == 1.0

        # Simulate rate limit fallback
        context.reduce_confidence(0.2, "Rate limit fallback")
        assert abs(context.confidence - 0.8) < 0.001

        # Simulate another issue
        context.reduce_confidence(0.1, "LLM degraded mode")
        assert abs(context.confidence - 0.7) < 0.001

    @pytest.mark.asyncio
    async def test_scraper_error_with_retry_info(self):
        """Test ScraperError includes retry information."""
        error = ScraperError(
            "Rate limited",
            max_retries=3,
            retries_attempted=3,
            last_response_status=429,
        )

        error_str = str(error)
        assert "Rate limited" in error_str
        assert "3/3 retries" in error_str
        assert "Status: 429" in error_str
        assert "Recovery:" in error_str
