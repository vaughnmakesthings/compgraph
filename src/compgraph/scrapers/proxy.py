"""Proxy and user-agent utilities for scraper HTTP clients."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from compgraph.config import Settings

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


def get_proxy_client_kwargs(settings: Settings) -> dict[str, Any]:
    """Return httpx.AsyncClient kwargs for proxy configuration.

    Returns an empty dict when no proxy is configured, allowing callers
    to unpack directly: ``httpx.AsyncClient(**get_proxy_client_kwargs(settings))``.
    """
    proxy_url = settings.proxy_url_with_auth
    if not proxy_url:
        return {}
    return {"proxy": proxy_url}
