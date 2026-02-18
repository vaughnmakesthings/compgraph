"""add server default for enrichment_runs.status

Revision ID: aa88b1c2d3e4
Revises: f8a9b0c1d2e3
Create Date: 2026-02-18 04:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "aa88b1c2d3e4"
down_revision: str = "f8a9b0c1d2e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("enrichment_runs", "status", server_default="pending")


def downgrade() -> None:
    op.alter_column("enrichment_runs", "status", server_default=None)
