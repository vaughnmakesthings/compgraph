import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from compgraph.api.routes.admin import router as admin_router
from compgraph.api.routes.aggregation import router as aggregation_router
from compgraph.api.routes.alerts import router as alerts_router
from compgraph.api.routes.companies import (
    router as companies_router,
)
from compgraph.api.routes.enrich import router as enrich_router
from compgraph.api.routes.health import router as health_router
from compgraph.api.routes.pipeline import router as pipeline_router
from compgraph.api.routes.postings import router as postings_router
from compgraph.api.routes.scheduler import router as scheduler_router
from compgraph.api.routes.scrape import router as scrape_router
from compgraph.auth.dependencies import (
    get_current_user,
    get_current_user_disabled,
    get_current_user_optional,
    require_admin,
    require_admin_disabled,
    require_viewer,
)
from compgraph.config import settings
from compgraph.db.session import engine
from compgraph.eval.router import router as eval_router

if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.anthropic import AnthropicIntegration
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.httpx import HttpxIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release="compgraph@0.1.0",
        server_name="compgraph-backend",
        enable_tracing=True,
        traces_sample_rate=0.2 if settings.ENVIRONMENT == "production" else 1.0,
        profiles_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
        send_default_pii=False,
        integrations=[
            AnthropicIntegration(include_prompts=False),
            FastApiIntegration(),
            SqlalchemyIntegration(),
            HttpxIntegration(),
            LoggingIntegration(
                level=logging.WARNING,
                event_level=logging.ERROR,
            ),
        ],
        _experiments={"continuous_profiling_auto_start": True},
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)


shutdown_event = asyncio.Event()


def _signal_handler(sig: int) -> None:
    """Handle SIGTERM/SIGINT by setting shutdown flag and stopping active pipelines."""
    # Import here to avoid circular import (main -> scrapers.orchestrator is safe,
    # but module-level import would execute before app is fully configured)
    from compgraph.scrapers.orchestrator import (
        PipelineStatus,
        _pipeline_runs,
        get_orchestrator,
    )

    sig_name = signal.Signals(sig).name
    logger.info("Received %s — initiating graceful shutdown", sig_name)
    shutdown_event.set()

    # Stop any active scrape pipeline runs gracefully
    active_runs = [
        r
        for r in _pipeline_runs.values()
        if r.status in (PipelineStatus.RUNNING, PipelineStatus.PAUSED)
    ]
    for run in active_runs:
        orch = get_orchestrator(run.run_id)
        if orch is not None:
            orch.stop(run)
            logger.info("Sent stop signal to pipeline run %s", run.run_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _signal_handler, sig)
    except (RuntimeError, NotImplementedError):
        # Signal handlers only work in main thread (fails in TestClient)
        pass

    app.state.shutdown_event = shutdown_event

    if settings.SCHEDULER_ENABLED:
        from compgraph.scheduler.app import setup_scheduler

        scheduler = await setup_scheduler()
        await scheduler.start_in_background()
        app.state.scheduler = scheduler
    yield
    logger.info("Lifespan cleanup starting")
    try:
        if settings.SCHEDULER_ENABLED and hasattr(app.state, "scheduler"):
            await app.state.scheduler.__aexit__(None, None, None)
    finally:
        await engine.dispose()
    logger.info("Lifespan cleanup complete")


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

if settings.AUTH_DISABLED:
    logger.warning("AUTH_DISABLED=true — all endpoints bypass authentication")
    app.dependency_overrides[get_current_user] = get_current_user_disabled
    app.dependency_overrides[require_admin] = require_admin_disabled
    app.dependency_overrides[require_viewer] = require_admin_disabled
    app.dependency_overrides[get_current_user_optional] = get_current_user_disabled

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(scrape_router)
v1_router.include_router(enrich_router)
v1_router.include_router(scheduler_router)
v1_router.include_router(pipeline_router)
v1_router.include_router(aggregation_router)
v1_router.include_router(companies_router)
v1_router.include_router(postings_router, prefix="/postings", tags=["postings"])
v1_router.include_router(eval_router, prefix="/eval", tags=["eval"])
v1_router.include_router(admin_router)
v1_router.include_router(alerts_router)

app.include_router(health_router)
app.include_router(v1_router)


@app.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    include_in_schema=False,
)
async def legacy_api_redirect(request: Request, path: str) -> RedirectResponse:
    if path.startswith("v1/") or path == "v1":
        raise HTTPException(status_code=404, detail="Not Found")
    query = f"?{request.query_params}" if request.query_params else ""
    return RedirectResponse(url=f"/api/v1/{path}{query}", status_code=308)
