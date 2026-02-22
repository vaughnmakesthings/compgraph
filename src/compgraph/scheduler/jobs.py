from __future__ import annotations

import logging
from datetime import UTC, datetime

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
)
from compgraph.scrapers.orchestrator import (
    _store_run as _store_scrape_run,
)

logger = logging.getLogger(__name__)

# In-process state — resets on server restart. After restart, missed-run
# detection will not trigger until the first pipeline run completes.
# Upgrade to persistent store (SQLAlchemy data store) in M6 if needed.
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


async def pipeline_job() -> None:
    global _last_pipeline_finished_at, _last_pipeline_success

    logger.info("[PIPELINE] Scheduled pipeline job starting")

    # --- Scrape phase ---
    logger.info("[SCRAPE] Starting scrape phase")
    pipeline_run = PipelineRun()
    _store_scrape_run(pipeline_run)
    orchestrator = PipelineOrchestrator()

    try:
        await orchestrator.run(pipeline_run)
    except Exception:
        logger.exception("[SCRAPE] Scrape phase failed with unhandled exception")
        pipeline_run.status = PipelineStatus.FAILED
        pipeline_run.finished_at = datetime.now(UTC)

    scrape_succeeded = pipeline_run.status in (
        PipelineStatus.SUCCESS,
        PipelineStatus.PARTIAL,
    )

    logger.info(
        "[SCRAPE] Scrape phase finished: status=%s, companies_succeeded=%d, "
        "companies_failed=%d, postings=%d",
        pipeline_run.status.value,
        pipeline_run.companies_succeeded,
        pipeline_run.companies_failed,
        pipeline_run.total_postings_found,
    )

    # --- Enrich phase ---
    enrich_succeeded = False
    if scrape_succeeded:
        logger.info("[ENRICH] Starting enrichment phase (scrape had successes)")
        enrichment_run = EnrichmentRun()
        _store_enrichment_run(enrichment_run)
        enrich_orchestrator = EnrichmentOrchestrator()

        try:
            await enrich_orchestrator.run_full(enrichment_run)
        except Exception:
            logger.exception("[ENRICH] Enrichment phase failed with unhandled exception")
            enrichment_run.status = EnrichmentStatus.FAILED
            enrichment_run.finished_at = datetime.now(UTC)

        enrich_succeeded = enrichment_run.status in (
            EnrichmentStatus.SUCCESS,
            EnrichmentStatus.PARTIAL,
        )

        logger.info(
            "[ENRICH] Enrichment phase finished: status=%s, pass1=%s, pass2=%s",
            enrichment_run.status.value,
            f"{enrichment_run.pass1_result.succeeded}ok/{enrichment_run.pass1_result.failed}fail"
            if enrichment_run.pass1_result
            else "none",
            f"{enrichment_run.pass2_result.succeeded}ok/{enrichment_run.pass2_result.failed}fail"
            if enrichment_run.pass2_result
            else "none",
        )
    else:
        logger.warning(
            "[ENRICH] Skipping enrichment — scrape fully failed (status=%s)",
            pipeline_run.status.value,
        )

    # --- Aggregate phase ---
    agg_succeeded = True
    if enrich_succeeded:
        logger.info("[AGGREGATE] Starting aggregation phase")
        try:
            from compgraph.aggregation.orchestrator import AggregationOrchestrator

            agg_orchestrator = AggregationOrchestrator()
            agg_result = await agg_orchestrator.run()
            agg_succeeded = agg_result.ok
            if agg_result.failed:
                logger.warning("[AGGREGATE] Partial failure: %s", agg_result.failed)
            logger.info(
                "[AGGREGATE] Aggregation phase finished: %d succeeded, %d failed",
                len(agg_result.succeeded),
                len(agg_result.failed),
            )
        except Exception:
            logger.exception("[AGGREGATE] Aggregation phase failed")
            agg_succeeded = False
    else:
        logger.warning("[AGGREGATE] Skipping aggregation — enrichment failed")
        agg_succeeded = False

    _last_pipeline_finished_at = datetime.now(UTC)
    _last_pipeline_success = scrape_succeeded and enrich_succeeded and agg_succeeded
    logger.info("[PIPELINE] Scheduled pipeline job complete")
