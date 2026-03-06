"""enforce RLS on all public tables

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-03-05 20:30:00.000000

The original RLS migration (7d1276046127) was stamped but never executed.
This migration actually enables RLS on all 24 public tables.

The app connects as postgres (has bypassrls), so no policies are needed.
Any rogue anon/authenticated connection will be blocked by RLS.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a8"
down_revision: str = "a1b2c3d4e5f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ALL_TABLES = [
    "companies",
    "brands",
    "retailers",
    "markets",
    "location_mappings",
    "scrape_runs",
    "enrichment_runs",
    "postings",
    "posting_snapshots",
    "posting_enrichments",
    "posting_brand_mentions",
    "agg_daily_velocity",
    "agg_brand_timeline",
    "agg_pay_benchmarks",
    "agg_posting_lifecycle",
    "agg_brand_churn_signals",
    "agg_market_coverage_gaps",
    "agg_brand_agency_overlap",
    "users",
    "eval_corpus",
    "eval_runs",
    "eval_results",
    "eval_comparisons",
    "eval_field_reviews",
]


def upgrade() -> None:
    for table in ALL_TABLES:
        op.execute(sa.text(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY"))


def downgrade() -> None:
    for table in ALL_TABLES:
        op.execute(sa.text(f"ALTER TABLE public.{table} NO FORCE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY"))
