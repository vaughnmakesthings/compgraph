"""Scrapers package: adapter protocol, registry, and orchestrator."""

from compgraph.scrapers.base import RawPosting, ScraperAdapter, ScrapeResult
from compgraph.scrapers.icims import ICIMSAdapter
from compgraph.scrapers.orchestrator import (
    CompanyState,
    PipelineOrchestrator,
    PipelineRun,
    PipelineStatus,
    _pipeline_orchestrators,
    get_orchestrator,
)
from compgraph.scrapers.registry import get_adapter, register_adapter
from compgraph.scrapers.workday import WorkdayAdapter

register_adapter("workday", WorkdayAdapter)

register_adapter("icims", ICIMSAdapter)

__all__ = [
    "CompanyState",
    "ICIMSAdapter",
    "PipelineOrchestrator",
    "PipelineRun",
    "PipelineStatus",
    "RawPosting",
    "ScrapeResult",
    "ScraperAdapter",
    "WorkdayAdapter",
    "_pipeline_orchestrators",
    "get_adapter",
    "get_orchestrator",
    "register_adapter",
]
