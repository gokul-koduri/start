"""Circuit Breaker — prevents cascading failures for external services.

Usage:
    from utils.circuit_breaker import ollama_breaker

    # Wrap external calls
    result = ollama_breaker.call(my_api_function, arg1, arg2)

    # Or use as context manager
    with stripe_breaker:
        stripe_api.charge(...)

States:
    CLOSED: Normal operation — calls pass through, failures are tracked
    OPEN: Service is down — calls raise CircuitOpenError immediately
    HALF_OPEN: Testing recovery — allows one probe call

Pre-built breakers for common services:
    - ollama_breaker: Ollama LLM API
    - stripe_breaker: Stripe payments API
    - search_breaker: External search APIs
"""

import logging
import time
from enum import Enum
from typing import Any, Callable, Optional

_logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when the circuit breaker is open and rejecting calls."""

    def __init__(self, service_name: str, state: CircuitState):
        self.service_name = service_name
        self.state = state
        super().__init__(
            f"Circuit breaker '{service_name}' is {state.value} — rejecting call"
        )


class CircuitBreaker:
    """Circuit breaker for external service calls.

    Args:
        name: Service name for logging.
        failure_threshold: Consecutive failures before opening (default: 5).
        recovery_timeout: Seconds before trying half-open (default: 60).
        success_threshold: Consecutive successes in half-open to close (default: 2).
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0
        self._last_failure_error: Optional[str] = None

    @property
    def state(self) -> CircuitState:
        """Current circuit state, with automatic half-open transition."""
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                _logger.info(
                    "CircuitBreaker '%s': OPEN -> HALF_OPEN (recovery timeout elapsed)",
                    self.name,
                )
        return self._state

    def call(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Call fn through the circuit breaker.

        Args:
            fn: The function to call.
            *args, **kwargs: Arguments to pass to fn.

        Returns:
            The return value of fn.

        Raises:
            CircuitOpenError: If the circuit is open.
            Exception: Re-raises any exception from fn (after recording failure).
        """
        current_state = self.state

        if current_state == CircuitState.OPEN:
            raise CircuitOpenError(self.name, current_state)

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    def _on_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                _logger.info(
                    "CircuitBreaker '%s': HALF_OPEN -> CLOSED (recovered)", self.name
                )
        else:
            self._failure_count = 0

    def _on_failure(self, error: Exception) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        self._last_failure_error = str(error)

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._success_count = 0
            _logger.warning(
                "CircuitBreaker '%s': HALF_OPEN -> OPEN (probe failed: %s)",
                self.name,
                error,
            )
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            _logger.warning(
                "CircuitBreaker '%s': CLOSED -> OPEN (%d consecutive failures)",
                self.name,
                self._failure_count,
            )

    def reset(self) -> None:
        """Manually reset the circuit to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        _logger.info("CircuitBreaker '%s': Manually reset to CLOSED", self.name)

    @property
    def status(self) -> dict:
        """Return circuit breaker status info."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "last_failure_error": self._last_failure_error,
            "last_failure_time": self._last_failure_time,
        }


# ── Pre-built circuit breakers ──

ollama_breaker = CircuitBreaker("ollama", failure_threshold=3, recovery_timeout=30)
stripe_breaker = CircuitBreaker("stripe", failure_threshold=5, recovery_timeout=60)
search_breaker = CircuitBreaker("search", failure_threshold=5, recovery_timeout=60)

# ── Stream pipeline circuit breakers ──

mysql_stream_breaker = CircuitBreaker(
    "mysql_stream", failure_threshold=5, recovery_timeout=30, success_threshold=3
)
kafka_stream_breaker = CircuitBreaker(
    "kafka_stream", failure_threshold=5, recovery_timeout=30, success_threshold=3
)
redis_stream_breaker = CircuitBreaker(
    "redis_stream", failure_threshold=3, recovery_timeout=30, success_threshold=2
)
