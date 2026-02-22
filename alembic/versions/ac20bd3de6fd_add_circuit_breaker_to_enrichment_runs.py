"""add circuit_breaker_tripped to enrichment_runs

Revision ID: ac20bd3de6fd
Revises: ff78a6b7c8d9
Create Date: 2026-02-21 00:45:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "ac20bd3de6fd"
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
