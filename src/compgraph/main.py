import logging
import sys
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from compgraph.api.routes.admin import router as admin_router
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

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.2 if settings.ENVIRONMENT == "production" else 1.0,
        integrations=[AnthropicIntegration(include_prompts=True)],
        send_default_pii=False,
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)


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

app.include_router(health_router)
app.include_router(v1_router)


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def legacy_api_redirect(request: Request, path: str) -> RedirectResponse:
    if path.startswith("v1/") or path == "v1":
        raise HTTPException(status_code=404, detail="Not Found")
    query = f"?{request.query_params}" if request.query_params else ""
    return RedirectResponse(url=f"/api/v1/{path}{query}", status_code=308)
