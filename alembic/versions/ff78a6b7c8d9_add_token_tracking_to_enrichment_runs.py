"""add token tracking columns to enrichment_runs

Track API token usage, call counts, and dedup savings per enrichment run
for cost visibility and operational monitoring.

Revision ID: ff78a6b7c8d9
Revises: ee67f5a6b7c8
Create Date: 2026-02-20 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "ff78a6b7c8d9"
down_revision = "ee67f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "enrichment_runs",
        sa.Column("total_input_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "enrichment_runs",
        sa.Column("total_output_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "enrichment_runs",
        sa.Column("total_api_calls", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "enrichment_runs",
        sa.Column("total_dedup_saved", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("enrichment_runs", "total_dedup_saved")
    op.drop_column("enrichment_runs", "total_api_calls")
    op.drop_column("enrichment_runs", "total_output_tokens")
    op.drop_column("enrichment_runs", "total_input_tokens")
