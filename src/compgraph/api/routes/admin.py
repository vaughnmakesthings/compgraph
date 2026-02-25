from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.api.deps import get_db, get_settings
from compgraph.auth.dependencies import AuthUser, require_admin
from compgraph.config import Settings
from compgraph.db.models import User

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

logger = logging.getLogger(__name__)


class InviteRequest(BaseModel):
    email: EmailStr
    role: Literal["admin", "viewer"] = "viewer"


class InviteResponse(BaseModel):
    email: str
    role: str
    invited: bool


class UserResponse(BaseModel):
    id: str
    auth_uid: str | None
    email: str
    name: str | None
    role: str
    created_at: datetime


@router.post("/invite", response_model=InviteResponse)
async def invite_user(
    body: InviteRequest,
    admin: AuthUser = Depends(require_admin),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_settings: Settings = Depends(get_settings),  # noqa: B008
) -> InviteResponse:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    service_role_key = current_settings.SUPABASE_SERVICE_ROLE_KEY.get_secret_value()

    async with httpx.AsyncClient(timeout=10.0) as client:
        invite_url = f"https://{current_settings.SUPABASE_PROJECT_REF}.supabase.co/auth/v1/invite"
        resp = await client.post(
            invite_url,
            json={
                "email": body.email,
                "data": {"role": body.role},
                "app_metadata": {"role": body.role},
            },
            headers={
                "Authorization": f"Bearer {service_role_key}",
                "apikey": service_role_key,
                "Content-Type": "application/json",
            },
        )

    if resp.status_code >= 400:
        logger.error(
            "Supabase invite failed: status=%d",
            resp.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send invite via Supabase Auth",
        )

    # Extract auth_uid from Supabase response to link local user to auth.users
    supabase_user = resp.json()
    auth_uid_str = supabase_user.get("id")
    auth_uid: uuid.UUID | None = None
    if auth_uid_str:
        try:
            auth_uid = uuid.UUID(auth_uid_str)
        except (ValueError, AttributeError):
            logger.warning("Supabase invite returned invalid id: %s", auth_uid_str)

    user = User(email=str(body.email), role=body.role, auth_uid=auth_uid)
    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        ) from None

    logger.info("User invited: role=%s invited_by=%s", body.role, admin.id)

    return InviteResponse(email=str(body.email), role=body.role, invited=True)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    _admin: AuthUser = Depends(require_admin),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[UserResponse]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        UserResponse(
            id=str(u.id),
            auth_uid=str(u.auth_uid) if u.auth_uid else None,
            email=u.email,
            name=u.name,
            role=u.role,
            created_at=u.created_at,
        )
        for u in users
    ]
