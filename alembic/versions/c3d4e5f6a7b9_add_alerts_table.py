"""Add alerts table for pipeline alert generation.

Revision ID: c3d4e5f6a7b9
Revises: a1b2c3d4e5f7
Create Date: 2026-03-05 21:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c3d4e5f6a7b9"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_company_type", "alerts", ["company_id", "alert_type"])
    op.create_index("ix_alerts_triggered_at", "alerts", ["triggered_at"])

    # Unique constraint for dedup: one alert per (type, company, brand, day)
    # Uses NULLS NOT DISTINCT so NULL brand_id values are treated as equal
    op.execute(
        sa.text("""
        CREATE UNIQUE INDEX uq_alert_dedup
        ON alerts (alert_type, company_id, brand_id, (triggered_at::date))
        NULLS NOT DISTINCT
    """)
    )


def downgrade() -> None:
    op.drop_index("uq_alert_dedup", table_name="alerts")
    op.drop_index("ix_alerts_triggered_at", table_name="alerts")
    op.drop_index("ix_alerts_company_type", table_name="alerts")
    op.drop_table("alerts")
