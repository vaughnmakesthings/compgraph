"""add missing FK indexes

Revision ID: cc45d3e4f5a6
Revises: bb47c2d3e4f5
Create Date: 2026-02-18 04:02:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "cc45d3e4f5a6"
down_revision: str = "bb47c2d3e4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FK_INDEXES = [
    ("ix_posting_enrichments_posting_id", "posting_enrichments", ["posting_id"]),
    ("ix_posting_brand_mentions_posting_id", "posting_brand_mentions", ["posting_id"]),
    ("ix_posting_enrichments_brand_id", "posting_enrichments", ["brand_id"]),
    ("ix_posting_enrichments_retailer_id", "posting_enrichments", ["retailer_id"]),
    ("ix_posting_enrichments_market_id", "posting_enrichments", ["market_id"]),
    (
        "ix_posting_brand_mentions_resolved_brand_id",
        "posting_brand_mentions",
        ["resolved_brand_id"],
    ),
    (
        "ix_posting_brand_mentions_resolved_retailer_id",
        "posting_brand_mentions",
        ["resolved_retailer_id"],
    ),
    ("ix_agg_daily_velocity_brand_id", "agg_daily_velocity", ["brand_id"]),
    ("ix_agg_daily_velocity_market_id", "agg_daily_velocity", ["market_id"]),
    ("ix_agg_pay_benchmarks_company_id", "agg_pay_benchmarks", ["company_id"]),
    ("ix_agg_pay_benchmarks_brand_id", "agg_pay_benchmarks", ["brand_id"]),
    ("ix_agg_pay_benchmarks_market_id", "agg_pay_benchmarks", ["market_id"]),
    ("ix_agg_posting_lifecycle_company_id", "agg_posting_lifecycle", ["company_id"]),
    ("ix_agg_posting_lifecycle_brand_id", "agg_posting_lifecycle", ["brand_id"]),
    ("ix_agg_posting_lifecycle_market_id", "agg_posting_lifecycle", ["market_id"]),
    ("ix_users_invited_by", "users", ["invited_by"]),
]


def upgrade() -> None:
    for name, table, columns in FK_INDEXES:
        op.create_index(name, table, columns)


def downgrade() -> None:
    for name, table, _columns in reversed(FK_INDEXES):
        op.drop_index(name, table_name=table)
