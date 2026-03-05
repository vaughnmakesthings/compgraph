from __future__ import annotations

from pydantic import BaseModel


class CompanyItem(BaseModel):
    id: str
    name: str
    slug: str
    ats_platform: str
