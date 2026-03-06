"""add missing perf indexes

Revision ID: 0657aded6e05
Revises: a9f0b1c2d3e4
Create Date: 2026-03-06 12:00:00.000000

Adds three indexes that become critical at scale:
- postings.first_seen_at — aggregation jobs filter on this
- posting_enrichments (posting_id, enriched_at DESC NULLS LAST) — DISTINCT ON
  queries currently sort the full table
- posting_snapshots.snapshot_date — DailyVelocityJob groups by this
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0657aded6e05"
down_revision: str | None = "a9f0b1c2d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text("CREATE INDEX IF NOT EXISTS ix_postings_first_seen_at ON postings (first_seen_at)")
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_posting_enrichments_posting_enriched "
            "ON posting_enrichments (posting_id, enriched_at DESC NULLS LAST)"
        )
    )
    op.execute(
        sa.text("CREATE INDEX IF NOT EXISTS ix_snapshots_date ON posting_snapshots (snapshot_date)")
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_snapshots_date"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_posting_enrichments_posting_enriched"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_postings_first_seen_at"))
