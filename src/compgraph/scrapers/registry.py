"""Adapter registry: maps ats_platform strings to adapter implementations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from compgraph.scrapers.base import ScraperAdapter

logger = logging.getLogger(__name__)

# Maps ats_platform value (from Company.ats_platform) to adapter class
_ADAPTER_REGISTRY: dict[str, type[ScraperAdapter]] = {}


def register_adapter(ats_platform: str, adapter_cls: type[ScraperAdapter]) -> None:
    """Register a scraper adapter for an ATS platform."""
    _ADAPTER_REGISTRY[ats_platform] = adapter_cls
    logger.info("Registered scraper adapter for %s: %s", ats_platform, adapter_cls.__name__)


def get_adapter(ats_platform: str) -> ScraperAdapter:
    """Instantiate and return the adapter for the given ATS platform.

    Raises:
        KeyError: If no adapter is registered for the given platform.
    """
    adapter_cls = _ADAPTER_REGISTRY[ats_platform]
    return adapter_cls()


def list_registered_platforms() -> list[str]:
    """Return all ATS platforms that have registered adapters."""
    return list(_ADAPTER_REGISTRY.keys())
