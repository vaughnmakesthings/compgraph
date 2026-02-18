"""add enrichment_runs table

Revision ID: b52ab5ef6cf1
Revises: e6f7a8b9c0d1
Create Date: 2026-02-16 17:21:27.441263

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b52ab5ef6cf1"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "enrichment_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pass1_total", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pass1_succeeded", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pass1_failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pass1_skipped", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pass2_total", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pass2_succeeded", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pass2_failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pass2_skipped", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_enrichment_runs_status_started",
        "enrichment_runs",
        [sa.text("status"), sa.text("started_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_enrichment_runs_status_started", table_name="enrichment_runs")
    op.drop_table("enrichment_runs")
