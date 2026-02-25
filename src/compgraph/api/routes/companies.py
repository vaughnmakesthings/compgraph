from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.api.deps import get_db
from compgraph.db.models import Company

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("")
async def list_companies(db: AsyncSession = Depends(get_db)) -> list[dict]:  # noqa: B008
    result = await db.execute(select(Company).order_by(Company.name))
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "slug": r.slug,
            "ats_platform": r.ats_platform,
        }
        for r in rows
    ]
