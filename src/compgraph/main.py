from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from compgraph.api.routes.health import router as health_router
from compgraph.config import settings
from compgraph.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: engine is already created at import time
    yield
    # Shutdown: dispose the connection pool
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
