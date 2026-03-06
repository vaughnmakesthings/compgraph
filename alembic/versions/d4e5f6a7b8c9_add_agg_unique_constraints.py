"""add unique constraints on aggregation tables

Revision ID: d4e5f6a7b8c9
Revises: 0657aded6e05
Create Date: 2026-03-06 14:00:00.000000

Prevents duplicate rows from concurrent aggregation rebuilds by adding
unique constraints on natural keys for all 7 aggregation tables.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "0657aded6e05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_velocity_date_company",
        "agg_daily_velocity",
        ["date", "company_id"],
    )
    op.create_unique_constraint(
        "uq_brand_timeline_company_brand",
        "agg_brand_timeline",
        ["company_id", "brand_id"],
    )
    # Nullable columns need NULLS NOT DISTINCT (PostgreSQL 15+)
    op.execute(
        "ALTER TABLE agg_pay_benchmarks ADD CONSTRAINT uq_pay_benchmarks_natural_key "
        "UNIQUE NULLS NOT DISTINCT (company_id, role_archetype, market_id, brand_id, period)"
    )
    op.execute(
        "ALTER TABLE agg_posting_lifecycle ADD CONSTRAINT uq_posting_lifecycle_natural_key "
        "UNIQUE NULLS NOT DISTINCT (company_id, role_archetype, brand_id, market_id, period)"
    )
    op.create_unique_constraint(
        "uq_churn_signals_company_brand_period",
        "agg_brand_churn_signals",
        ["company_id", "brand_id", "period"],
    )
    op.create_unique_constraint(
        "uq_coverage_gaps_company_market_period",
        "agg_market_coverage_gaps",
        ["company_id", "market_id", "period"],
    )
    op.create_unique_constraint(
        "uq_agency_overlap_brand_period",
        "agg_brand_agency_overlap",
        ["brand_id", "period"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_agency_overlap_brand_period", "agg_brand_agency_overlap", type_="unique")
    op.drop_constraint(
        "uq_coverage_gaps_company_market_period", "agg_market_coverage_gaps", type_="unique"
    )
    op.drop_constraint(
        "uq_churn_signals_company_brand_period", "agg_brand_churn_signals", type_="unique"
    )
    op.drop_constraint("uq_posting_lifecycle_natural_key", "agg_posting_lifecycle", type_="unique")
    op.drop_constraint("uq_pay_benchmarks_natural_key", "agg_pay_benchmarks", type_="unique")
    op.drop_constraint("uq_brand_timeline_company_brand", "agg_brand_timeline", type_="unique")
    op.drop_constraint("uq_velocity_date_company", "agg_daily_velocity", type_="unique")
