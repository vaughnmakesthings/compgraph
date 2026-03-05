"""Service layer for company queries — extracted from api/routes/companies.py."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.db.models import Company


class CompanyService:
    """Encapsulates company-related database queries."""

    @staticmethod
    async def list_companies(db: AsyncSession) -> list[dict]:
        result = await db.execute(select(Company).order_by(Company.name))
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "slug": r.slug,
                "ats_platform": r.ats_platform,
            }
            for r in result.scalars().all()
        ]
