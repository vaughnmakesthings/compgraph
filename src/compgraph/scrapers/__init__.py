"""Scrapers package: adapter protocol, registry, and orchestrator."""

from compgraph.scrapers.base import RawPosting, ScraperAdapter, ScrapeResult
from compgraph.scrapers.icims import ICIMSAdapter
from compgraph.scrapers.orchestrator import (
    PipelineOrchestrator,
    PipelineRun,
    PipelineStatus,
)
from compgraph.scrapers.registry import get_adapter, register_adapter
from compgraph.scrapers.workday import WorkdayAdapter

register_adapter("workday", WorkdayAdapter)

register_adapter("icims", ICIMSAdapter)

__all__ = [
    "ICIMSAdapter",
    "PipelineOrchestrator",
    "PipelineRun",
    "PipelineStatus",
    "RawPosting",
    "ScrapeResult",
    "ScraperAdapter",
    "WorkdayAdapter",
    "get_adapter",
    "register_adapter",
]
