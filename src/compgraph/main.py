import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from compgraph.api.routes.aggregation import router as aggregation_router
from compgraph.api.routes.companies import (
    router as companies_router,
)
from compgraph.api.routes.enrich import router as enrich_router
from compgraph.api.routes.health import router as health_router
from compgraph.api.routes.pipeline import router as pipeline_router
from compgraph.api.routes.postings import router as postings_router
from compgraph.api.routes.scheduler import router as scheduler_router
from compgraph.api.routes.scrape import router as scrape_router
from compgraph.config import settings
from compgraph.db.session import engine
from compgraph.eval.router import router as eval_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stderr,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.SCHEDULER_ENABLED:
        from compgraph.scheduler.app import setup_scheduler

        scheduler = await setup_scheduler()
        await scheduler.start_in_background()
        app.state.scheduler = scheduler
    yield
    try:
        if settings.SCHEDULER_ENABLED and hasattr(app.state, "scheduler"):
            await app.state.scheduler.__aexit__(None, None, None)
    finally:
        await engine.dispose()


app = FastAPI(
    title="CompGraph",
    description="Competitive intelligence platform for field marketing agencies",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(scrape_router)
app.include_router(enrich_router)
app.include_router(scheduler_router)
app.include_router(pipeline_router)
app.include_router(aggregation_router)
app.include_router(companies_router)
app.include_router(postings_router, prefix="/api/postings", tags=["postings"])
app.include_router(eval_router, prefix="/api/eval", tags=["eval"])
