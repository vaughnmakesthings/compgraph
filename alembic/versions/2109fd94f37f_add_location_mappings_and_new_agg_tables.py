"""add location_mappings and new agg tables

Revision ID: 2109fd94f37f
Revises: afa58cde6b1e
Create Date: 2026-02-22 00:31:56.976295

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2109fd94f37f"
down_revision: Union[str, None] = "afa58cde6b1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create location_mappings table
    op.create_table(
        "location_mappings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("city_normalized", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=10), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column("metro_name", sa.String(length=255), nullable=False),
        sa.Column("metro_state", sa.String(length=10), nullable=False),
        sa.Column("metro_country", sa.String(length=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("city_normalized", "state", "country", name="uq_location_mapping"),
    )

    # 2. Add country column to markets
    op.add_column("markets", sa.Column("country", sa.String(length=2), nullable=True))

    # 3. Create agg_brand_churn_signals table
    op.create_table(
        "agg_brand_churn_signals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("brand_id", sa.UUID(), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("active_posting_count", sa.Integer(), nullable=False),
        sa.Column("prior_period_count", sa.Integer(), nullable=False),
        sa.Column("velocity_delta", sa.Float(), nullable=True),
        sa.Column("avg_days_active", sa.Float(), nullable=True),
        sa.Column("repost_rate", sa.Float(), nullable=True),
        sa.Column("churn_signal_score", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_churn_signals_company_brand",
        "agg_brand_churn_signals",
        ["company_id", "brand_id"],
        unique=False,
    )

    # 4. Create agg_market_coverage_gaps table
    op.create_table(
        "agg_market_coverage_gaps",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("market_id", sa.UUID(), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("total_active_postings", sa.Integer(), nullable=False),
        sa.Column("brand_count", sa.Integer(), nullable=False),
        sa.Column("brand_names", sa.ARRAY(sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["market_id"], ["markets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_coverage_gaps_company_market",
        "agg_market_coverage_gaps",
        ["company_id", "market_id"],
        unique=False,
    )

    # 5. Create agg_brand_agency_overlap table
    op.create_table(
        "agg_brand_agency_overlap",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("brand_id", sa.UUID(), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("agency_count", sa.Integer(), nullable=False),
        sa.Column("agency_names", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("primary_company_id", sa.UUID(), nullable=True),
        sa.Column("primary_share", sa.Float(), nullable=True),
        sa.Column("is_exclusive", sa.Boolean(), nullable=False),
        sa.Column("is_contested", sa.Boolean(), nullable=False),
        sa.Column("total_postings", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.ForeignKeyConstraint(["primary_company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agency_overlap_brand", "agg_brand_agency_overlap", ["brand_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_agency_overlap_brand", table_name="agg_brand_agency_overlap")
    op.drop_table("agg_brand_agency_overlap")
    op.drop_index("ix_coverage_gaps_company_market", table_name="agg_market_coverage_gaps")
    op.drop_table("agg_market_coverage_gaps")
    op.drop_index("ix_churn_signals_company_brand", table_name="agg_brand_churn_signals")
    op.drop_table("agg_brand_churn_signals")
    op.drop_column("markets", "country")
    op.drop_table("location_mappings")
