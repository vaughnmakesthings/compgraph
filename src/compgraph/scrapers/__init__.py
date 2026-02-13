"""Scrapers package: adapter protocol, registry, and orchestrator."""

from compgraph.scrapers.base import RawPosting, ScraperAdapter, ScrapeResult
from compgraph.scrapers.orchestrator import (
    PipelineOrchestrator,
    PipelineRun,
    PipelineStatus,
)
from compgraph.scrapers.registry import get_adapter, register_adapter

__all__ = [
    "PipelineOrchestrator",
    "PipelineRun",
    "PipelineStatus",
    "RawPosting",
    "ScrapeResult",
    "ScraperAdapter",
    "get_adapter",
    "register_adapter",
]
