"""Resilient client wrapper with circuit-breaker pattern and graceful degradation.

This module provides utilities for making API calls that gracefully handle:
- Rate limits (429)
- Server errors (5xx)
- Connection failures
- Empty/malformed responses
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, TypeVar
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitBreakerState:
    """Enum-like class for circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests go through
    OPEN = "open"          # Failing, requests are blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker pattern implementation for API calls.

    Prevents cascading failures by stopping requests to a failing service
    and periodically testing if the service has recovered.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._state = CircuitBreakerState.CLOSED

    @property
    def state(self) -> str:
        """Get current circuit breaker state."""
        if self._state == CircuitBreakerState.OPEN:
            # Check if we should transition to half-open
            if self._last_failure_time:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self.recovery_timeout:
                    self._state = CircuitBreakerState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        """Record a successful call."""
        self._failure_count = 0
        self._state = CircuitBreakerState.CLOSED

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitBreakerState.OPEN
            logger.warning(
                "Circuit breaker opened after %d failures",
                self._failure_count,
            )

    def can_execute(self) -> bool:
        """Check if a request can be executed."""
        return self.state != CircuitBreakerState.OPEN


class ResilientClient:
    """Wrapper that provides circuit-breaker pattern with graceful degradation.

    Usage:
        client = ResilientClient(provider_name="MyAPI")
        result = client.call_with_fallback(
            primary_fn=lambda: my_api.call(),
            fallback_fn=lambda: return_default_value,
            max_retries=3,
        )
    """

    def __init__(
        self,
        provider_name: str = "API",
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ):
        self.provider_name = provider_name
        self.breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    def call_with_retry(
        self,
        func: Callable[[], T],
        max_retries: int = 3,
        backoff_base: float = 1.0,
        retry_on: tuple = (Exception,),
    ) -> T | None:
        """Call a function with exponential backoff retries.

        Args:
            func: The function to call.
            max_retries: Maximum number of retry attempts.
            backoff_base: Base for exponential backoff in seconds.
            retry_on: Tuple of exception types to retry on.

        Returns:
            The function result, or None if all retries failed.
        """
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                result = func()
                self.breaker.record_success()
                return result
            except retry_on as e:
                last_error = e
                self.breaker.record_failure()

                if attempt < max_retries:
                    wait = backoff_base * (2 ** (attempt - 1))
                    logger.warning(
                        "%s: call failed (attempt %d/%d), retrying in %.1fs: %s",
                        self.provider_name,
                        attempt,
                        max_retries,
                        wait,
                        e,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "%s: call failed after %d attempts: %s",
                        self.provider_name,
                        max_retries,
                        e,
                    )

        return None

    def call_with_fallback(
        self,
        primary_fn: Callable[[], T],
        fallback_fn: Callable[[], T] | None = None,
        max_retries: int = 3,
    ) -> T | Any | None:
        """Call primary function with circuit breaker, fallback on failure.

        Args:
            primary_fn: Primary function to call.
            fallback_fn: Fallback function if primary fails (optional).
            max_retries: Maximum retries for primary function.

        Returns:
            Primary result, fallback result, or None if both fail.
        """
        # Check circuit breaker
        if not self.breaker.can_execute():
            logger.info(
                "%s: circuit breaker open, skipping to fallback",
                self.provider_name,
            )
            if fallback_fn:
                return fallback_fn()
            return None

        # Try primary with retry
        result = self.call_with_retry(primary_fn, max_retries=max_retries)

        if result is not None:
            return result

        # Primary failed, try fallback
        if fallback_fn:
            logger.info(
                "%s: primary failed, attempting fallback",
                self.provider_name,
            )
            try:
                return fallback_fn()
            except Exception as e:
                logger.error(
                    "%s: fallback also failed: %s",
                    self.provider_name,
                    e,
                )

        return None


def with_resilience(
    provider_name: str = "API",
    max_retries: int = 3,
    backoff_base: float = 1.0,
    fallback: T | None = None,
) -> Callable:
    """Decorator to add resilience to a function.

    Usage:
        @with_resilience(provider_name="MyAPI", max_retries=3)
        def my_api_call():
            return some_api.call()
    """
    def decorator(func: Callable[[], T]) -> Callable[[], T | None]:
        client = ResilientClient(provider_name=provider_name)

        @wraps(func)
        def wrapper() -> T | None:
            return client.call_with_retry(
                func,
                max_retries=max_retries,
                backoff_base=backoff_base,
            ) if fallback is None else client.call_with_fallback(
                func,
                fallback_fn=lambda: fallback,
                max_retries=max_retries,
            )

        return wrapper

    return decorator