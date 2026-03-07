from __future__ import annotations

import pytest

from compgraph.scrapers.circuit_breaker import CircuitBreakerMixin, CircuitBreakerOpen


class ConcreteBreaker(CircuitBreakerMixin):
    def __init__(self, threshold: int = 3, label: str = "") -> None:
        self._init_circuit_breaker(threshold=threshold, label=label)


class TestCircuitBreakerMixin:
    def test_initial_state(self) -> None:
        cb = ConcreteBreaker()
        assert cb.circuit_open is False
        assert cb.consecutive_failures == 0

    def test_record_success_resets_failures(self) -> None:
        cb = ConcreteBreaker(threshold=5)
        cb._record_failure()
        cb._record_failure()
        assert cb.consecutive_failures == 2
        cb._record_success()
        assert cb.consecutive_failures == 0
        assert cb.circuit_open is False

    def test_trips_at_threshold(self) -> None:
        cb = ConcreteBreaker(threshold=3)
        cb._record_failure()
        cb._record_failure()
        assert cb.circuit_open is False
        cb._record_failure()
        assert cb.circuit_open is True
        assert cb.consecutive_failures == 3

    def test_check_circuit_raises_when_open(self) -> None:
        cb = ConcreteBreaker(threshold=1)
        cb._record_failure()
        assert cb.circuit_open is True
        with pytest.raises(CircuitBreakerOpen):
            cb._check_circuit()

    def test_check_circuit_passes_when_closed(self) -> None:
        cb = ConcreteBreaker(threshold=3)
        cb._record_failure()
        cb._check_circuit()  # should not raise

    def test_label_in_error_message(self) -> None:
        cb = ConcreteBreaker(threshold=1, label="test-service")
        cb._record_failure()
        with pytest.raises(CircuitBreakerOpen, match="test-service"):
            cb._check_circuit()

    def test_no_label_in_error_message(self) -> None:
        cb = ConcreteBreaker(threshold=1, label="")
        cb._record_failure()
        with pytest.raises(CircuitBreakerOpen, match="Circuit breaker open after 1"):
            cb._check_circuit()

    def test_threshold_one(self) -> None:
        cb = ConcreteBreaker(threshold=1)
        assert cb.circuit_open is False
        cb._record_failure()
        assert cb.circuit_open is True

    def test_success_does_not_reset_open_state(self) -> None:
        cb = ConcreteBreaker(threshold=2)
        cb._record_failure()
        cb._record_failure()
        assert cb.circuit_open is True
        cb._record_success()
        assert cb.consecutive_failures == 0
        # circuit_open stays True -- no auto-reset
        assert cb.circuit_open is True
