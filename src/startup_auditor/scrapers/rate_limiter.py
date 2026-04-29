"""Rate limiter with exponential backoff for Startup-Auditor scrapers.

Implements retry logic with:
- Exponential backoff (1s, 4s, 9s for 3 retries)
- Retry-After header support (capped at 10s)
- Jitter to prevent thundering herd (±10%)
- Support for both HTTP 429 and connection errors
"""

import asyncio
import random
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from typing import Callable, Any

from startup_auditor.exceptions import ScraperError


@dataclass
class RetryResult:
    """Result of a retry operation.

    Attributes:
        success: Whether the operation succeeded
        result: The result value (if successful)
        retries_attempted: Number of retry attempts made
        error: The last error encountered (if failed)
    """
    success: bool
    result: Any = None
    retries_attempted: int = 0
    error: Exception | None = None


class RateLimiter:
    """Rate limiter with exponential backoff and retry logic.

    Features:
    - Configurable max retries (default: 3)
    - Exponential backoff: delay = (attempt + 1) ** 2 seconds
    - Retry-After header parsing (integer seconds and HTTP-date format)
    - Jitter: ±10% randomization to prevent thundering herd
    - Cap on Retry-After: 10 seconds maximum

    Usage:
        limiter = RateLimiter(max_retries=3)
        result = await limiter.execute_with_retry(my_async_func)
    """

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0) -> None:
        """Initialize rate limiter.

        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Base delay in seconds for backoff calculation (default: 1.0)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay

    def calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds with ±10% jitter applied
        """
        # Exponential backoff: (attempt + 1) ** 2 = 1, 4, 9, ...
        delay = self.base_delay * ((attempt + 1) ** 2)
        # Add ±10% jitter
        jitter = random.uniform(-0.1, 0.1) * delay
        return delay + jitter

    def parse_retry_after(self, header_value: str) -> float:
        """Parse Retry-After header value.

        Args:
            header_value: Value from Retry-After header

        Returns:
            Seconds to wait, capped at 10.0 seconds
        """
        try:
            # Integer seconds format
            return min(int(header_value), 10.0)
        except ValueError:
            # HTTP-date format (e.g., "Wed, 21 Oct 2015 07:28:00 GMT")
            try:
                retry_date = parsedate_to_datetime(header_value)
                delta = (retry_date - datetime.now(timezone.utc)).total_seconds()
                return max(0.0, min(delta, 10.0))
            except (ValueError, TypeError):
                # If parsing fails, fall back to default backoff
                return self.calculate_backoff(0)

    def is_retryable_error(self, error: Exception, status_code: int | None = None) -> bool:
        """Check if an error is retryable.

        Args:
            error: The exception that was raised
            status_code: HTTP status code (if applicable)

        Returns:
            True if the error should trigger a retry
        """
        # HTTP 429 Too Many Requests
        if status_code == 429:
            return True

        # Connection errors that are likely temporary
        error_name = type(error).__name__.lower()
        retryable_errors = [
            "timeout",
            "connection",
            "dns",
        ]

        return any(name in error_name for name in retryable_errors)

    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        on_retry: Callable | None = None,
        **kwargs,
    ) -> RetryResult:
        """Execute an async function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments to pass to func
            on_retry: Optional callback called on each retry with (attempt, error, delay)
            **kwargs: Keyword arguments to pass to func

        Returns:
            RetryResult with success status and result/error
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                return RetryResult(
                    success=True,
                    result=result,
                    retries_attempted=attempt,
                )
            except Exception as e:
                last_error = e

                # Check if we should retry
                if not self.is_retryable_error(e):
                    return RetryResult(
                        success=False,
                        error=e,
                        retries_attempted=attempt,
                    )

                # If this was the last attempt, don't retry
                if attempt == self.max_retries:
                    break

                # Call on_retry callback if provided
                if on_retry:
                    on_retry(attempt, e, 0)  # delay not known yet

                # Calculate delay and sleep
                delay = self.calculate_backoff(attempt)
                await asyncio.sleep(delay)

        # All retries exhausted
        return RetryResult(
            success=False,
            error=last_error,
            retries_attempted=self.max_retries,
        )
