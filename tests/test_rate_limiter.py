"""Tests for per-domain rate limiter."""

from __future__ import annotations

import time

import pytest

from compgraph.scrapers.rate_limiter import (
    DEFAULT_RATE,
    DEFAULT_RATES,
    get_limiter,
    reset_limiters,
)


@pytest.fixture(autouse=True)
def isolate_limiters():
    """Reset the module-level limiter cache between tests."""
    reset_limiters()
    yield
    reset_limiters()


class TestGetLimiter:
    """Tests for get_limiter()."""

    def test_returns_async_limiter(self) -> None:
        from aiolimiter import AsyncLimiter

        limiter = get_limiter("icims.com")
        assert isinstance(limiter, AsyncLimiter)

    def test_same_domain_returns_same_instance(self) -> None:
        limiter1 = get_limiter("icims.com")
        limiter2 = get_limiter("icims.com")
        assert limiter1 is limiter2

    def test_different_domains_return_different_instances(self) -> None:
        limiter1 = get_limiter("icims.com")
        limiter2 = get_limiter("myworkdayjobs.com")
        assert limiter1 is not limiter2

    def test_known_domains_use_configured_rate(self) -> None:
        for domain, expected_rate in DEFAULT_RATES.items():
            reset_limiters()
            limiter = get_limiter(domain)
            assert limiter.max_rate == expected_rate, f"Expected {expected_rate} req/s for {domain}"

    def test_unknown_domain_uses_default_rate(self) -> None:
        limiter = get_limiter("unknown-ats.example.com")
        assert limiter.max_rate == DEFAULT_RATE

    def test_explicit_rate_override(self) -> None:
        limiter = get_limiter("example.com", rate=10.0)
        assert limiter.max_rate == 10.0

    def test_rate_override_ignored_on_second_call(self) -> None:
        """Second call returns cached limiter — rate arg is ignored."""
        get_limiter("example.com", rate=10.0)
        limiter = get_limiter("example.com", rate=99.0)
        assert limiter.max_rate == 10.0  # cached value wins


class TestResetLimiters:
    def test_reset_clears_cache(self) -> None:
        l1 = get_limiter("icims.com")
        reset_limiters()
        l2 = get_limiter("icims.com")
        assert l1 is not l2

    def test_reset_allows_new_rate(self) -> None:
        get_limiter("icims.com", rate=1.0)
        reset_limiters()
        limiter = get_limiter("icims.com", rate=7.0)
        assert limiter.max_rate == 7.0


class TestDefaultRates:
    def test_icims_rate_configured(self) -> None:
        assert "icims.com" in DEFAULT_RATES
        assert DEFAULT_RATES["icims.com"] > 0

    def test_workday_rate_configured(self) -> None:
        assert "myworkdayjobs.com" in DEFAULT_RATES
        assert DEFAULT_RATES["myworkdayjobs.com"] > 0

    def test_jobsyn_rate_configured(self) -> None:
        assert "jobsyn.org" in DEFAULT_RATES
        assert DEFAULT_RATES["jobsyn.org"] > 0

    def test_default_rate_positive(self) -> None:
        assert DEFAULT_RATE > 0


@pytest.mark.asyncio
class TestLimiterAsyncBehaviour:
    async def test_limiter_allows_first_request_immediately(self) -> None:
        """First acquisition from a fresh limiter should complete quickly."""
        limiter = get_limiter("test-fast.example.com", rate=100.0)
        start = time.monotonic()
        async with limiter:
            pass
        elapsed = time.monotonic() - start
        assert elapsed < 0.5, f"First acquire took too long: {elapsed:.3f}s"

    async def test_context_manager_protocol(self) -> None:
        """AsyncLimiter works as an async context manager."""
        limiter = get_limiter("ctx-test.example.com", rate=100.0)
        acquired = False
        async with limiter:
            acquired = True
        assert acquired
