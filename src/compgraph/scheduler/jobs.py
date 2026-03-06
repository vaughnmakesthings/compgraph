from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import sentry_sdk

from compgraph.enrichment.orchestrator import (
    EnrichmentOrchestrator,
    EnrichmentRun,
    EnrichmentStatus,
)
from compgraph.enrichment.orchestrator import (
    _store_run as _store_enrichment_run,
)
from compgraph.scrapers.orchestrator import (
    PipelineOrchestrator,
    PipelineRun,
    PipelineStatus,
    _pipeline_orchestrators,
)
from compgraph.scrapers.orchestrator import (
    _store_run as _store_scrape_run,
)

if TYPE_CHECKING:
    from sentry_sdk._types import MonitorConfig

logger = logging.getLogger(__name__)

_MONITOR_CONFIG: MonitorConfig = {
    "schedule": {"type": "crontab", "value": "0 2 * * 1,3,5"},
    "timezone": "America/New_York",
    "checkin_margin": 10,
    "max_runtime": 120,
    "failure_issue_threshold": 1,
    "recovery_threshold": 1,
}

_last_pipeline_finished_at: datetime | None = None
_last_pipeline_success: bool = False


def get_last_pipeline_finished_at() -> datetime | None:
    return _last_pipeline_finished_at


def get_last_pipeline_success() -> bool:
    return _last_pipeline_success


async def get_last_pipeline_run_from_db() -> dict[str, datetime | bool | None]:
    from sqlalchemy import select

    from compgraph.db.models import ScrapeRun
    from compgraph.db.session import async_session_factory

    async with async_session_factory() as session:
        stmt = (
            select(ScrapeRun.completed_at, ScrapeRun.status)
            .where(ScrapeRun.status == "completed")
            .order_by(ScrapeRun.completed_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        row = result.first()
        if row is None:
            return {"finished_at": None, "success": False}
        return {"finished_at": row.completed_at, "success": True}


@sentry_sdk.monitor(
    monitor_slug="daily-pipeline",
    monitor_config=_MONITOR_CONFIG,  # type: ignore[arg-type]
)
async def pipeline_job() -> None:
    global _last_pipeline_finished_at, _last_pipeline_success

    logger.info("[PIPELINE] Scheduled pipeline job starting")

    # Deferred import to avoid circular dependency (jobs -> main -> health -> ...)
    from compgraph.main import shutdown_event

    # --- Cleanup stale PENDING runs before starting ---
    try:
        from compgraph.db.session import async_session_factory
        from compgraph.scrapers.orchestrator import cleanup_stale_pending_runs

        async with async_session_factory() as session:
            cleaned = await cleanup_stale_pending_runs(session)
            if cleaned:
                logger.info("[PIPELINE] Cleaned up %d stale PENDING runs", cleaned)
    except Exception:
        logger.exception("[PIPELINE] Failed to clean up stale PENDING runs")
        sentry_sdk.capture_exception()

    # --- Scrape phase ---
    with sentry_sdk.start_span(op="pipeline.scrape", name="Scrape ATS sites"):
        logger.info("[SCRAPE] Starting scrape phase")
        pipeline_run = PipelineRun()
        _store_scrape_run(pipeline_run)
        orchestrator = PipelineOrchestrator()

        # Register orchestrator so signal handler can stop scheduler-triggered runs
        _pipeline_orchestrators[pipeline_run.run_id] = orchestrator

        try:
            await orchestrator.run(pipeline_run)
        except Exception:
            logger.exception("[SCRAPE] Scrape phase failed with unhandled exception")
            sentry_sdk.capture_exception()
            pipeline_run.status = PipelineStatus.FAILED
            pipeline_run.finished_at = datetime.now(UTC)
        finally:
            _pipeline_orchestrators.pop(pipeline_run.run_id, None)

        scrape_succeeded = pipeline_run.status in (
            PipelineStatus.SUCCESS,
            PipelineStatus.PARTIAL,
        )

        sentry_sdk.set_context(
            "pipeline_scrape",
            {
                "phase": "scrape",
                "status": pipeline_run.status.value,
                "companies_succeeded": pipeline_run.companies_succeeded,
                "companies_failed": pipeline_run.companies_failed,
                "postings_found": pipeline_run.total_postings_found,
            },
        )

        logger.info(
            "[SCRAPE] Scrape phase finished: status=%s, companies_succeeded=%d, "
            "companies_failed=%d, postings=%d",
            pipeline_run.status.value,
            pipeline_run.companies_succeeded,
            pipeline_run.companies_failed,
            pipeline_run.total_postings_found,
        )

    # --- Check for shutdown before continuing ---

    if shutdown_event.is_set():
        logger.warning("[PIPELINE] Shutdown signal received — skipping remaining phases")
        _last_pipeline_finished_at = datetime.now(UTC)
        _last_pipeline_success = False
        return

    # --- Enrich phase ---
    enrich_succeeded = False
    if scrape_succeeded:
        with sentry_sdk.start_span(op="pipeline.enrich", name="LLM enrichment (Haiku + Sonnet)"):
            logger.info("[ENRICH] Starting enrichment phase (scrape had successes)")
            enrichment_run = EnrichmentRun()
            _store_enrichment_run(enrichment_run)
            enrich_orchestrator = EnrichmentOrchestrator()

            try:
                await enrich_orchestrator.run_full(enrichment_run)
            except Exception:
                logger.exception("[ENRICH] Enrichment phase failed with unhandled exception")
                sentry_sdk.capture_exception()
                enrichment_run.status = EnrichmentStatus.FAILED
                enrichment_run.finished_at = datetime.now(UTC)

            enrich_succeeded = enrichment_run.status in (
                EnrichmentStatus.SUCCESS,
                EnrichmentStatus.PARTIAL,
            )

            pass1_summary = (
                f"{enrichment_run.pass1_result.succeeded}ok/"
                f"{enrichment_run.pass1_result.failed}fail"
                if enrichment_run.pass1_result
                else "none"
            )
            pass2_summary = (
                f"{enrichment_run.pass2_result.succeeded}ok/"
                f"{enrichment_run.pass2_result.failed}fail"
                if enrichment_run.pass2_result
                else "none"
            )

            sentry_sdk.set_context(
                "pipeline_enrich",
                {
                    "phase": "enrich",
                    "status": enrichment_run.status.value,
                    "pass1": pass1_summary,
                    "pass2": pass2_summary,
                },
            )

            logger.info(
                "[ENRICH] Enrichment phase finished: status=%s, pass1=%s, pass2=%s",
                enrichment_run.status.value,
                pass1_summary,
                pass2_summary,
            )
    else:
        logger.warning(
            "[ENRICH] Skipping enrichment — scrape fully failed (status=%s)",
            pipeline_run.status.value,
        )

    if shutdown_event.is_set():
        logger.warning("[PIPELINE] Shutdown signal received — skipping aggregation")
        _last_pipeline_finished_at = datetime.now(UTC)
        _last_pipeline_success = False
        return

    # --- Aggregate phase ---
    agg_succeeded = True
    if enrich_succeeded:
        with sentry_sdk.start_span(op="pipeline.aggregate", name="Rebuild aggregation tables"):
            logger.info("[AGGREGATE] Starting aggregation phase")
            try:
                from compgraph.aggregation.orchestrator import AggregationOrchestrator

                agg_orchestrator = AggregationOrchestrator()
                agg_result = await agg_orchestrator.run()
                agg_succeeded = agg_result.ok
                if agg_result.failed:
                    logger.warning("[AGGREGATE] Partial failure: %s", agg_result.failed)

                sentry_sdk.set_context(
                    "pipeline_aggregate",
                    {
                        "phase": "aggregate",
                        "succeeded_tables": list(agg_result.succeeded),
                        "failed_tables": list(agg_result.failed),
                    },
                )

                logger.info(
                    "[AGGREGATE] Aggregation phase finished: %d succeeded, %d failed",
                    len(agg_result.succeeded),
                    len(agg_result.failed),
                )
            except Exception:
                logger.exception("[AGGREGATE] Aggregation phase failed")
                sentry_sdk.capture_exception()
                agg_succeeded = False
    else:
        logger.warning("[AGGREGATE] Skipping aggregation — enrichment failed")
        agg_succeeded = False

    # --- Alert generation phase ---
    alerts_succeeded = True
    if agg_succeeded:
        with sentry_sdk.start_span(op="pipeline.alerts", name="Generate alerts"):
            logger.info("[ALERTS] Starting alert generation")
            try:
                from compgraph.aggregation.alerts import generate_alerts

                alert_counts = await generate_alerts()
                total_alerts = sum(alert_counts.values())
                sentry_sdk.set_context(
                    "pipeline_alerts",
                    {"phase": "alerts", "counts": alert_counts, "total": total_alerts},
                )
                logger.info("[ALERTS] Alert generation complete: %d alerts", total_alerts)
            except Exception:
                logger.exception("[ALERTS] Alert generation failed")
                sentry_sdk.capture_exception()
                alerts_succeeded = False
    else:
        logger.warning("[ALERTS] Skipping alert generation — aggregation failed")
        alerts_succeeded = False

    _last_pipeline_finished_at = datetime.now(UTC)
    _last_pipeline_success = (
        scrape_succeeded and enrich_succeeded and agg_succeeded and alerts_succeeded
    )
    logger.info("[PIPELINE] Scheduled pipeline job complete")
