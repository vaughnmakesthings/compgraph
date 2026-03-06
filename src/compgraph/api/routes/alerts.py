"""Alerts API — read-only endpoint for generated alerts."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.api.deps import get_db
from compgraph.auth.dependencies import require_viewer
from compgraph.db.models import Alert

router = APIRouter(
    prefix="/alerts",
    tags=["alerts"],
    dependencies=[Depends(require_viewer)],
)


class AlertItem(BaseModel):
    id: uuid.UUID
    alert_type: str
    company_id: uuid.UUID
    brand_id: uuid.UUID | None
    triggered_at: datetime
    metadata_json: dict | None


class AlertListResponse(BaseModel):
    items: list[AlertItem]
    total: int


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    company_id: uuid.UUID | None = None,
    alert_type: str | None = None,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> AlertListResponse:
    from sqlalchemy import func

    count_stmt = select(func.count(Alert.id))
    data_stmt = select(Alert).order_by(Alert.triggered_at.desc(), Alert.id)

    if company_id is not None:
        count_stmt = count_stmt.where(Alert.company_id == company_id)
        data_stmt = data_stmt.where(Alert.company_id == company_id)
    if alert_type is not None:
        count_stmt = count_stmt.where(Alert.alert_type == alert_type)
        data_stmt = data_stmt.where(Alert.alert_type == alert_type)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (await db.execute(data_stmt.limit(limit).offset(offset))).scalars().all()

    return AlertListResponse(
        items=[
            AlertItem(
                id=a.id,
                alert_type=a.alert_type,
                company_id=a.company_id,
                brand_id=a.brand_id,
                triggered_at=a.triggered_at,
                metadata_json=a.metadata_json,
            )
            for a in rows
        ],
        total=total,
    )
