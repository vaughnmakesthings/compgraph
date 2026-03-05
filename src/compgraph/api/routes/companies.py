from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.api.deps import get_db
from compgraph.api.schemas.companies import CompanyItem
from compgraph.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyItem])
async def list_companies(db: AsyncSession = Depends(get_db)) -> list[dict]:  # noqa: B008
    return await CompanyService.list_companies(db)
