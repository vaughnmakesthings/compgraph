"""Proxy and user-agent utilities for scraper HTTP clients."""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable
from urllib.parse import urlparse

if TYPE_CHECKING:
    from compgraph.config import Settings

logger = logging.getLogger(__name__)

# Current mainstream browser user agents (updated Feb 2026)
_USER_AGENTS = [
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15"
    ),
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
]


def random_user_agent() -> str:
    """Return a random browser user-agent string."""
    return random.choice(_USER_AGENTS)  # noqa: S311


# ---------------------------------------------------------------------------
# ProxyProvider protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ProxyProvider(Protocol):
    """Protocol for proxy provider implementations."""

    async def get_proxy_url(self, domain: str) -> str | None:
        """Return a proxy URL for the given domain, or None to use direct connection."""
        ...

    def report_success(self, domain: str) -> None:
        """Record a successful request to domain (for health tracking)."""
        ...

    def report_failure(self, domain: str) -> None:
        """Record a failed request to domain (for health tracking)."""
        ...


# ---------------------------------------------------------------------------
# StaticProxyProvider
# ---------------------------------------------------------------------------


class StaticProxyProvider:
    """Wraps a single static proxy URL.  Mirrors the original proxy.py behaviour."""

    def __init__(self, proxy_url: str) -> None:
        self._proxy_url = proxy_url
        self._failures: dict[str, int] = {}
        self._successes: dict[str, int] = {}

    async def get_proxy_url(self, domain: str) -> str | None:
        return self._proxy_url

    def report_success(self, domain: str) -> None:
        self._successes[domain] = self._successes.get(domain, 0) + 1
        self._failures[domain] = 0

    def report_failure(self, domain: str) -> None:
        self._failures[domain] = self._failures.get(domain, 0) + 1
        logger.debug("Static proxy failure #%d for %s", self._failures[domain], domain)


# ---------------------------------------------------------------------------
# OxylabsProvider
# ---------------------------------------------------------------------------


class OxylabsProvider:
    """Oxylabs residential proxy with per-request rotation and optional sticky sessions.

    Constructs HTTPS proxy URLs in the form:
        https://<username>-country-us:<password>@pr.oxylabs.io:7777

    Per-request rotation is the default (no session ID).  Pass
    ``sticky_session=True`` to use a session ID derived from the domain,
    which keeps the same exit node for the duration of a scrape run.
    """

    _HOST = "pr.oxylabs.io"
    _PORT = 7777

    def __init__(
        self,
        username: str,
        password: str,
        country: str = "us",
        sticky_session: bool = False,
    ) -> None:
        self._username = username
        self._password = password
        self._country = country
        self._sticky_session = sticky_session
        self._failures: dict[str, int] = {}
        self._successes: dict[str, int] = {}

    def _build_url(self, domain: str) -> str:
        user = f"{self._username}-country-{self._country}"
        if self._sticky_session:
            # Deterministic session ID per domain (numeric, Oxylabs requirement)
            session_id = abs(hash(domain)) % 10_000
            user = f"{user}-sessid-{session_id}"
        return f"https://{user}:{self._password}@{self._HOST}:{self._PORT}"

    async def get_proxy_url(self, domain: str) -> str | None:
        return self._build_url(domain)

    def report_success(self, domain: str) -> None:
        self._successes[domain] = self._successes.get(domain, 0) + 1
        self._failures[domain] = 0

    def report_failure(self, domain: str) -> None:
        self._failures[domain] = self._failures.get(domain, 0) + 1
        logger.warning(
            "Oxylabs proxy failure #%d for domain %s",
            self._failures[domain],
            domain,
        )


# ---------------------------------------------------------------------------
# ProxyPool
# ---------------------------------------------------------------------------


class ProxyPool:
    """Domain-aware proxy pool that auto-detects the provider from the proxy URL.

    Auto-detection logic:
    - hostname contains ``oxylabs.io``  → OxylabsProvider
    - anything else                     → StaticProxyProvider

    Credentials are passed via Settings (PROXY_USERNAME / PROXY_PASSWORD).
    """

    def __init__(self, settings: Settings) -> None:
        self._provider: ProxyProvider | None = self._build_provider(settings)

    @staticmethod
    def _build_provider(settings: Settings) -> ProxyProvider | None:
        proxy_url = settings.proxy_url_with_auth
        if not proxy_url:
            return None

        raw_url = settings.PROXY_URL or ""
        hostname = urlparse(raw_url).hostname or ""

        if "oxylabs.io" in hostname:
            username = settings.PROXY_USERNAME or ""
            password = settings.PROXY_PASSWORD.get_secret_value() if settings.PROXY_PASSWORD else ""
            return OxylabsProvider(username=username, password=password)

        # Fallback: plain static proxy
        return StaticProxyProvider(proxy_url=proxy_url)

    async def get_proxy_url(self, domain: str) -> str | None:
        if self._provider is None:
            return None
        return await self._provider.get_proxy_url(domain)

    def report_success(self, domain: str) -> None:
        if self._provider is not None:
            self._provider.report_success(domain)

    def report_failure(self, domain: str) -> None:
        if self._provider is not None:
            self._provider.report_failure(domain)


# ---------------------------------------------------------------------------
# Module-level pool (singleton per settings instance)
# ---------------------------------------------------------------------------

_pool: ProxyPool | None = None


def _get_pool(settings: Settings) -> ProxyPool:
    global _pool
    if _pool is None:
        _pool = ProxyPool(settings)
    return _pool


# ---------------------------------------------------------------------------
# Public API (backwards-compatible + domain-aware)
# ---------------------------------------------------------------------------


def get_proxy_client_kwargs(settings: Settings, domain: str = "") -> dict[str, Any]:
    """Return httpx.AsyncClient kwargs for proxy configuration.

    Accepts an optional ``domain`` parameter for domain-aware routing.  When
    ``domain`` is omitted the pool falls back to the configured static URL.

    Returns an empty dict when no proxy is configured, allowing callers to
    unpack directly: ``httpx.AsyncClient(**get_proxy_client_kwargs(settings))``.

    Note: This is a synchronous wrapper.  For fully async domain-aware routing
    use ``ProxyPool.get_proxy_url()`` directly.
    """
    proxy_url = settings.proxy_url_with_auth
    if not proxy_url:
        return {}

    raw_url = settings.PROXY_URL or ""
    hostname = urlparse(raw_url).hostname or ""

    if domain and "oxylabs.io" in hostname:
        # Build Oxylabs URL synchronously for httpx client construction
        username = settings.PROXY_USERNAME or ""
        password = settings.PROXY_PASSWORD.get_secret_value() if settings.PROXY_PASSWORD else ""
        provider = OxylabsProvider(username=username, password=password)
        # Use domain-specific URL
        return {"proxy": provider._build_url(domain)}

    return {"proxy": proxy_url}
