"""add posting and snapshot unique constraints

Revision ID: a1b2c3d4e5f6
Revises: 046d37447ab0
Create Date: 2026-02-13 13:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "046d37447ab0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Remove any existing duplicates before adding the unique constraint.
    # Keeps the row with the latest created_at for each (posting_id, snapshot_date).
    op.execute(
        sa.text("""
            DELETE FROM posting_snapshots
            WHERE id IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY posting_id, snapshot_date
                               ORDER BY created_at DESC
                           ) AS rn
                    FROM posting_snapshots
                ) ranked
                WHERE rn > 1
            )
        """)
    )
    op.create_unique_constraint(
        "uq_snapshots_posting_date",
        "posting_snapshots",
        ["posting_id", "snapshot_date"],
    )
    # Remove any existing duplicate postings before adding the unique constraint.
    # Keeps the row with the earliest first_seen_at for each (company_id, external_job_id).
    op.execute(
        sa.text("""
            DELETE FROM postings
            WHERE id IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY company_id, external_job_id
                               ORDER BY first_seen_at ASC
                           ) AS rn
                    FROM postings
                ) ranked
                WHERE rn > 1
            )
        """)
    )
    op.create_unique_constraint(
        "uq_postings_company_external",
        "postings",
        ["company_id", "external_job_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_postings_company_external", "postings")
    op.drop_constraint("uq_snapshots_posting_date", "posting_snapshots")
