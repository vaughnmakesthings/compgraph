from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class VelocityItem(BaseModel):
    id: uuid.UUID
    date: date
    company_id: uuid.UUID
    brand_id: uuid.UUID | None
    market_id: uuid.UUID | None
    active_postings: int
    new_postings: int
    closed_postings: int
    net_change: int
    company_name: str
    company_slug: str


class BrandTimelineItem(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    brand_id: uuid.UUID
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    is_currently_active: bool
    total_postings_all_time: int
    current_active_postings: int
    peak_active_postings: int
    peak_date: date | None
    brand_name: str
    company_name: str
    company_slug: str


class PayBenchmarkItem(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    role_archetype: str | None
    market_id: uuid.UUID | None
    brand_id: uuid.UUID | None
    period: date
    avg_pay_min: float | None
    avg_pay_max: float | None
    median_pay_min: float | None
    median_pay_max: float | None
    sample_size: int


class LifecycleItem(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    role_archetype: str | None
    brand_id: uuid.UUID | None
    market_id: uuid.UUID | None
    period: date
    avg_days_open: float | None
    median_days_open: float | None
    repost_rate: float | None
    avg_repost_gap_days: float | None


class ChurnSignalItem(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    brand_id: uuid.UUID
    period: date
    active_posting_count: int
    prior_period_count: int
    velocity_delta: float | None
    avg_days_active: float | None
    repost_rate: float | None
    churn_signal_score: float | None


class CoverageGapItem(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    market_id: uuid.UUID
    period: date
    total_active_postings: int
    brand_count: int
    brand_names: list[str] | None


class AgencyOverlapItem(BaseModel):
    id: uuid.UUID
    brand_id: uuid.UUID
    period: date
    agency_count: int
    agency_names: list[str] | None
    primary_company_id: uuid.UUID | None
    primary_share: float | None
    is_exclusive: bool
    is_contested: bool
    total_postings: int
