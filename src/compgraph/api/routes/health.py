import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from compgraph.api.deps import get_db

router = APIRouter()

DB_CHECK_TIMEOUT = 2.0


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> JSONResponse:  # noqa: B008
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=DB_CHECK_TIMEOUT)
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "version": "0.1.0", "database": "connected"},
        )
    except Exception as exc:
        detail = str(exc) if str(exc) else type(exc).__name__
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "version": "0.1.0",
                "database": f"error: {detail}",
            },
        )
