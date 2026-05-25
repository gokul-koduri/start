"""Token-bucket rate limiter for API requests."""

import time
import threading
import logging

_logger = logging.getLogger(__name__)


class RateLimiter:
    """Token-bucket rate limiter.

    Usage:
        limiter = RateLimiter(requests_per_minute=10)
        for item in items:
            limiter.wait()
            make_request(item)
    """

    def __init__(self, requests_per_minute: float = 10):
        self.rate = requests_per_minute
        self.tokens = requests_per_minute
        self.max_tokens = requests_per_minute
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * (self.rate / 60.0))
        self.last_refill = now

    def wait(self):
        """Block until a token is available, then consume it."""
        with self._lock:
            self._refill()
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / (self.rate / 60.0)
                _logger.debug("Rate limit: waiting %.1f seconds", wait_time)
                time.sleep(wait_time)
                self._refill()
            self.tokens -= 1
