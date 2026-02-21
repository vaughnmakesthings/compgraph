"""add circuit_breaker_tripped to enrichment_runs

Revision ID: a1b2c3d4e5f6
Revises: ff78a6b7c8d9
Create Date: 2026-02-21 00:45:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "ff78a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "enrichment_runs",
        sa.Column(
            "circuit_breaker_tripped",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("enrichment_runs", "circuit_breaker_tripped")
