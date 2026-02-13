"""add scrape_runs table

Revision ID: a1b2c3d4e5f6
Revises: 046d37447ab0
Create Date: 2026-02-13 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "046d37447ab0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scrape_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("pages_scraped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("snapshots_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scrape_runs_company_started",
        "scrape_runs",
        ["company_id", sa.text("started_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_scrape_runs_company_started", table_name="scrape_runs")
    op.drop_table("scrape_runs")
