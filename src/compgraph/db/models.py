import enum
import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
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
    text,
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
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    postings: Mapped[list["Posting"]] = relationship(back_populates="company")
    scrape_runs: Mapped[list["ScrapeRun"]] = relationship(back_populates="company")


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
    country: Mapped[str | None] = mapped_column(String(2), nullable=True, default="US")
    dma: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LocationMapping(Base):
    __tablename__ = "location_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    city_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(10), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="US")
    metro_name: Mapped[str] = mapped_column(String(255), nullable=False)
    metro_state: Mapped[str] = mapped_column(String(10), nullable=False)
    metro_country: Mapped[str] = mapped_column(String(2), nullable=False, default="US")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("city_normalized", "state", "country", name="uq_location_mapping"),
    )


# ---------------------------------------------------------------------------
# Fact tables
# ---------------------------------------------------------------------------


class ScrapeRunStatus(enum.StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ScrapeRunStatus.PENDING)
    pages_scraped: Mapped[int] = mapped_column(Integer, default=0)
    jobs_found: Mapped[int] = mapped_column(Integer, default=0)
    snapshots_created: Mapped[int] = mapped_column(Integer, default=0)
    postings_closed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    errors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="scrape_runs")

    __table_args__ = (Index("ix_scrape_runs_company_started", "company_id", started_at.desc()),)


class EnrichmentRunStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EnrichmentRunDB(Base):
    __tablename__ = "enrichment_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EnrichmentRunStatus.PENDING
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pass1_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    pass1_succeeded: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    pass1_failed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    pass1_skipped: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    pass2_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    pass2_succeeded: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    pass2_failed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    pass2_skipped: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    total_input_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    total_output_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    total_api_calls: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    total_dedup_saved: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    circuit_breaker_tripped: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_enrichment_runs_status_started", "status", started_at.desc()),)


class Posting(Base):
    __tablename__ = "postings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    external_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fingerprint_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    times_reposted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    h3_index: Mapped[str | None] = mapped_column(String(15), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="postings")
    snapshots: Mapped[list["PostingSnapshot"]] = relationship(back_populates="posting")
    enrichments: Mapped[list["PostingEnrichment"]] = relationship(back_populates="posting")
    brand_mentions: Mapped[list["PostingBrandMention"]] = relationship(back_populates="posting")

    __table_args__ = (
        UniqueConstraint("company_id", "external_job_id", name="uq_postings_company_external"),
        Index("ix_postings_fingerprint_hash", "fingerprint_hash"),
        Index("ix_postings_brand_active", "company_id", "is_active"),
        Index("ix_postings_first_seen_at", "first_seen_at", postgresql_using="btree"),
        Index(
            "idx_postings_h3",
            "h3_index",
            postgresql_where=text("h3_index IS NOT NULL"),
        ),
    )


class PostingSnapshot(Base):
    __tablename__ = "posting_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    posting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("postings.id", ondelete="CASCADE"), nullable=False
    )
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
        Index("ix_snapshots_date", "snapshot_date", postgresql_using="btree"),
        UniqueConstraint("posting_id", "snapshot_date", name="uq_snapshots_posting_date"),
    )


class PostingEnrichment(Base):
    __tablename__ = "posting_enrichments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    posting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("postings.id", ondelete="CASCADE"), nullable=False
    )

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
    entity_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Embedding
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)

    # Enrichment tracking
    enrichment_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    enrichment_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    posting: Mapped["Posting"] = relationship(back_populates="enrichments")

    __table_args__ = (
        Index("ix_posting_enrichment_posting_version", "posting_id", "enrichment_version"),
        Index(
            "ix_posting_enrichments_posting_enriched",
            "posting_id",
            enriched_at.desc().nulls_last(),
        ),
        Index("ix_posting_enrichment_brand_id", "brand_id"),
        Index("ix_posting_enrichment_retailer_id", "retailer_id"),
        Index("ix_posting_enrichment_market_id", "market_id"),
        CheckConstraint("pay_min IS NULL OR pay_min >= 0", name="check_pay_min_positive"),
        CheckConstraint("pay_max IS NULL OR pay_max >= 0", name="check_pay_max_positive"),
        CheckConstraint(
            "pay_min IS NULL OR pay_max IS NULL OR pay_min <= pay_max",
            name="check_pay_range",
        ),
        CheckConstraint(
            "entity_count IS NULL OR entity_count >= 0",
            name="check_entity_count_non_negative",
        ),
    )


class PostingBrandMention(Base):
    __tablename__ = "posting_brand_mentions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    posting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("postings.id", ondelete="CASCADE"), nullable=False
    )
    entity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_brand_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("brands.id", ondelete="RESTRICT"), nullable=True
    )
    resolved_retailer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("retailers.id", ondelete="SET NULL"), nullable=True
    )

    posting: Mapped["Posting"] = relationship(back_populates="brand_mentions")

    __table_args__ = (
        Index("ix_posting_brand_mention_posting_entity", "posting_id", "entity_type"),
    )


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

    __table_args__ = (
        UniqueConstraint("date", "company_id", name="uq_velocity_date_company"),
        Index("ix_velocity_date_company", "date", "company_id"),
    )


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

    __table_args__ = (
        UniqueConstraint("company_id", "brand_id", name="uq_brand_timeline_company_brand"),
        Index("ix_brand_timeline_company_brand", "company_id", "brand_id"),
    )


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

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "role_archetype",
            "market_id",
            "brand_id",
            "period",
            name="uq_pay_benchmarks_natural_key",
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_agg_pay_benchmarks_company_role", "company_id", "role_archetype"),
    )


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

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "role_archetype",
            "brand_id",
            "market_id",
            "period",
            name="uq_posting_lifecycle_natural_key",
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_agg_posting_lifecycle_company_period", "company_id", "period"),
    )


class AggBrandChurnSignals(Base):
    __tablename__ = "agg_brand_churn_signals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id"), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    active_posting_count: Mapped[int] = mapped_column(Integer, default=0)
    prior_period_count: Mapped[int] = mapped_column(Integer, default=0)
    velocity_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_days_active: Mapped[float | None] = mapped_column(Float, nullable=True)
    repost_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    churn_signal_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "company_id", "brand_id", "period", name="uq_churn_signals_company_brand_period"
        ),
        Index("ix_churn_signals_company_brand", "company_id", "brand_id"),
    )


class AggMarketCoverageGaps(Base):
    __tablename__ = "agg_market_coverage_gaps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    market_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("markets.id"), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    total_active_postings: Mapped[int] = mapped_column(Integer, default=0)
    brand_count: Mapped[int] = mapped_column(Integer, default=0)
    brand_names: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "company_id", "market_id", "period", name="uq_coverage_gaps_company_market_period"
        ),
        Index("ix_coverage_gaps_company_market", "company_id", "market_id"),
    )


class AggBrandAgencyOverlap(Base):
    __tablename__ = "agg_brand_agency_overlap"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id"), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    agency_count: Mapped[int] = mapped_column(Integer, default=0)
    agency_names: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    primary_company_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("companies.id"), nullable=True
    )
    primary_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_exclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    is_contested: Mapped[bool] = mapped_column(Boolean, default=False)
    total_postings: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("brand_id", "period", name="uq_agency_overlap_brand_period"),
        Index("ix_agency_overlap_brand", "brand_id"),
    )


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("brands.id"), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_alerts_company_type", "company_id", "alert_type"),
        Index("ix_alerts_triggered_at", "triggered_at"),
    )


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Logical reference to auth.users.id — NO ForeignKey (Alembic excludes auth schema)
    auth_uid: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, unique=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")
    invited_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
