"""Circuit breaker tests — validates state transitions, recovery, and error handling (T-118)."""

import unittest
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCircuitBreaker(unittest.TestCase):
    """Test CircuitBreaker state transitions."""

    def test_initial_state_closed(self):
        """New breaker should be CLOSED."""
        from utils.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker("test")
        self.assertEqual(cb.state, CircuitState.CLOSED)

    def test_call_succeeds_when_closed(self):
        """Calls pass through when CLOSED."""
        from utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker("test")
        result = cb.call(lambda: 42)
        self.assertEqual(result, 42)

    def test_opens_after_threshold(self):
        """Opens after consecutive failures reach threshold."""
        from utils.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker("test", failure_threshold=3)

        for _ in range(3):
            try:
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
            except ValueError:
                pass

        self.assertEqual(cb.state, CircuitState.OPEN)

    def test_rejects_when_open(self):
        """Raises CircuitOpenError when OPEN."""
        from utils.circuit_breaker import CircuitBreaker, CircuitOpenError

        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=300)

        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass

        with self.assertRaises(CircuitOpenError):
            cb.call(lambda: 42)

    def test_half_open_after_recovery_timeout(self):
        """Transitions to HALF_OPEN after recovery_timeout."""
        from utils.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)

        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass

        self.assertEqual(cb.state, CircuitState.OPEN)
        time.sleep(0.15)
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)

    def test_half_open_to_closed_on_success(self):
        """Closes after success_threshold successes in HALF_OPEN."""
        from utils.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker(
            "test", failure_threshold=1, recovery_timeout=0.1, success_threshold=2
        )

        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass

        time.sleep(0.15)
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)

        cb.call(lambda: "ok1")
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
        cb.call(lambda: "ok2")
        self.assertEqual(cb.state, CircuitState.CLOSED)

    def test_half_open_to_open_on_failure(self):
        """Returns to OPEN if probe call fails in HALF_OPEN."""
        from utils.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.1)

        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass

        time.sleep(0.15)
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)

        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("probe fail")))
        except ValueError:
            pass

        self.assertEqual(cb.state, CircuitState.OPEN)

    def test_reset(self):
        """Manual reset returns to CLOSED."""
        from utils.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker("test", failure_threshold=1)

        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass

        self.assertEqual(cb.state, CircuitState.OPEN)
        cb.reset()
        self.assertEqual(cb.state, CircuitState.CLOSED)

    def test_status_dict(self):
        """status returns dict with state info."""
        from utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker("test")
        status = cb.status
        self.assertEqual(status["name"], "test")
        self.assertEqual(status["state"], "closed")
        self.assertEqual(status["failure_count"], 0)

    def test_prebuilt_breakers_exist(self):
        """Pre-built breakers are importable."""
        from utils.circuit_breaker import ollama_breaker, stripe_breaker, search_breaker

        self.assertEqual(ollama_breaker.name, "ollama")
        self.assertEqual(stripe_breaker.name, "stripe")
        self.assertEqual(search_breaker.name, "search")

    def test_failure_count_resets_on_success(self):
        """Failure count resets when a call succeeds in CLOSED state."""
        from utils.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker("test", failure_threshold=5)

        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except ValueError:
            pass
        self.assertEqual(cb._failure_count, 1)

        cb.call(lambda: "ok")
        self.assertEqual(cb._failure_count, 0)


if __name__ == "__main__":
    unittest.main()
