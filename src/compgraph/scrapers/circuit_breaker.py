from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class CircuitBreakerOpen(Exception):
    pass


class CircuitBreakerMixin:
    _consecutive_failures: int
    _circuit_open: bool
    _circuit_breaker_threshold: int
    _circuit_breaker_label: str

    def _init_circuit_breaker(
        self,
        threshold: int = 3,
        label: str = "",
    ) -> None:
        self._consecutive_failures = 0
        self._circuit_open = False
        self._circuit_breaker_threshold = threshold
        self._circuit_breaker_label = label

    def _record_success(self) -> None:
        self._consecutive_failures = 0

    def _record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._circuit_breaker_threshold:
            self._circuit_open = True
            logger.error(
                "Circuit breaker OPEN after %d consecutive failures%s",
                self._consecutive_failures,
                f" for {self._circuit_breaker_label}" if self._circuit_breaker_label else "",
            )

    def _check_circuit(self) -> None:
        if self._circuit_open:
            raise CircuitBreakerOpen(
                f"Circuit breaker open after {self._consecutive_failures} consecutive failures"
                + (f" for {self._circuit_breaker_label}" if self._circuit_breaker_label else "")
            )

    @property
    def circuit_open(self) -> bool:
        return self._circuit_open

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures
