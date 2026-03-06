"""Per-domain rate limiting for scraper HTTP clients.

Uses aiolimiter.AsyncLimiter to enforce a maximum number of requests per
second per ATS domain.  Limiters are lazily created and cached module-wide,
so all adapter instances within the same process share the same token buckets.

Usage::

    from compgraph.scrapers.rate_limiter import get_limiter

    async with get_limiter("icims.com"):
        response = await client.get(url)
"""

from __future__ import annotations

import logging

from aiolimiter import AsyncLimiter

logger = logging.getLogger(__name__)

# Shared limiter registry — one AsyncLimiter per domain.
_domain_limiters: dict[str, AsyncLimiter] = {}

# Default maximum requests per second per known ATS platform.
DEFAULT_RATES: dict[str, float] = {
    "icims.com": 2.0,
    "myworkdayjobs.com": 5.0,
    "jobsyn.org": 3.0,
}

# Fallback rate for unknown domains.
DEFAULT_RATE = 2.0


def get_limiter(domain: str, rate: float | None = None) -> AsyncLimiter:
    """Return (or lazily create) the AsyncLimiter for the given domain.

    Args:
        domain: ATS hostname, e.g. ``"icims.com"``.
        rate:   Override the default rate (requests/second).  Only applied
                on first creation — subsequent calls with the same domain
                return the cached limiter regardless of ``rate``.
    """
    if domain not in _domain_limiters:
        effective_rate = rate if rate is not None else DEFAULT_RATES.get(domain, DEFAULT_RATE)
        # AsyncLimiter(max_rate, time_period) — time_period=1 means per-second.
        _domain_limiters[domain] = AsyncLimiter(effective_rate, 1)
        logger.debug(
            "Created rate limiter for %s: %.1f req/s",
            domain,
            effective_rate,
        )
    return _domain_limiters[domain]


def reset_limiters() -> None:
    """Clear all cached limiters.  Intended for use in tests only."""
    _domain_limiters.clear()
