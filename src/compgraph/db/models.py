import uuid
from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Dimension tables
# ---------------------------------------------------------------------------


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    ats_platform: Mapped[str] = mapped_column(String(50), nullable=False)
    career_site_url: Mapped[str] = mapped_column(Text, nullable=False)
    scraper_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    postings: Mapped[list["Posting"]] = relationship(back_populates="company")


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Retailer(Base):
    __tablename__ = "retailers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    channel_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    dma: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Fact tables
# ---------------------------------------------------------------------------


class Posting(Base):
    __tablename__ = "postings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    external_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fingerprint_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    times_reposted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="postings")
    snapshots: Mapped[list["PostingSnapshot"]] = relationship(back_populates="posting")
    enrichments: Mapped[list["PostingEnrichment"]] = relationship(back_populates="posting")
    brand_mentions: Mapped[list["PostingBrandMention"]] = relationship(back_populates="posting")

    __table_args__ = (
        Index("ix_postings_fingerprint_hash", "fingerprint_hash"),
        Index("ix_postings_brand_active", "company_id", "is_active"),
    )


class PostingSnapshot(Base):
    __tablename__ = "posting_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    posting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("postings.id"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    title_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_changed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    posting: Mapped["Posting"] = relationship(back_populates="snapshots")

    __table_args__ = (
        Index("ix_snapshots_company_brand_date", "posting_id", "snapshot_date"),
        UniqueConstraint("posting_id", "snapshot_date", name="uq_snapshots_posting_date"),
    )


class PostingEnrichment(Base):
    __tablename__ = "posting_enrichments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    posting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("postings.id"), nullable=False)

    # Classification
    title_normalized: Mapped[str | None] = mapped_column(Text, nullable=True)
    role_archetype: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role_level: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Entities
    brand_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("brands.id"), nullable=True)
    retailer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("retailers.id"), nullable=True)
    market_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("markets.id"), nullable=True)

    # Compensation
    pay_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pay_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    pay_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    pay_currency: Mapped[str | None] = mapped_column(String(3), nullable=True, default="USD")
    pay_frequency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    commission_mentioned: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    commission_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    benefits_mentioned: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    benefits_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Content sections
    content_role_specific: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_boilerplate: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_qualifications: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    tools_mentioned: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    kpis_mentioned: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    store_count_mentioned: Mapped[int | None] = mapped_column(Integer, nullable=True)
    travel_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Enrichment tracking
    enrichment_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    enrichment_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    posting: Mapped["Posting"] = relationship(back_populates="enrichments")


class PostingBrandMention(Base):
    __tablename__ = "posting_brand_mentions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    posting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("postings.id"), nullable=False)
    entity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_brand_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("brands.id"), nullable=True
    )
    resolved_retailer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("retailers.id"), nullable=True
    )

    posting: Mapped["Posting"] = relationship(back_populates="brand_mentions")


# ---------------------------------------------------------------------------
# Aggregation tables (materialized — rebuilt daily)
# ---------------------------------------------------------------------------


class AggDailyVelocity(Base):
    __tablename__ = "agg_daily_velocity"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("brands.id"), nullable=True)
    market_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("markets.id"), nullable=True)
    active_postings: Mapped[int] = mapped_column(Integer, default=0)
    new_postings: Mapped[int] = mapped_column(Integer, default=0)
    closed_postings: Mapped[int] = mapped_column(Integer, default=0)
    net_change: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (Index("ix_velocity_date_company", "date", "company_id"),)


class AggBrandTimeline(Base):
    __tablename__ = "agg_brand_timeline"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id"), nullable=False)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_currently_active: Mapped[bool] = mapped_column(Boolean, default=False)
    total_postings_all_time: Mapped[int] = mapped_column(Integer, default=0)
    current_active_postings: Mapped[int] = mapped_column(Integer, default=0)
    peak_active_postings: Mapped[int] = mapped_column(Integer, default=0)
    peak_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (Index("ix_brand_timeline_company_brand", "company_id", "brand_id"),)


class AggPayBenchmarks(Base):
    __tablename__ = "agg_pay_benchmarks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    role_archetype: Mapped[str | None] = mapped_column(String(100), nullable=True)
    market_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("markets.id"), nullable=True)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("brands.id"), nullable=True)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    avg_pay_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_pay_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    median_pay_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    median_pay_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)


class AggPostingLifecycle(Base):
    __tablename__ = "agg_posting_lifecycle"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    role_archetype: Mapped[str | None] = mapped_column(String(100), nullable=True)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("brands.id"), nullable=True)
    market_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("markets.id"), nullable=True)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    avg_days_open: Mapped[float | None] = mapped_column(Float, nullable=True)
    median_days_open: Mapped[float | None] = mapped_column(Float, nullable=True)
    repost_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_repost_gap_days: Mapped[float | None] = mapped_column(Float, nullable=True)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")
    invited_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
