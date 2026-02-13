"""add snapshot posting_id snapshot_date unique constraint

Revision ID: a1b2c3d4e5f6
Revises: 046d37447ab0
Create Date: 2026-02-13 13:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "046d37447ab0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_snapshots_posting_date",
        "posting_snapshots",
        ["posting_id", "snapshot_date"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_snapshots_posting_date", "posting_snapshots")
