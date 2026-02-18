"""drop append-only trigger from posting_enrichments

The enrichment pipeline legitimately updates enrichment_version
(pass1-v1 -> pass1-v1+pass2) and brand_id/retailer_id on existing
enrichment records. The append-only trigger blocks these updates.

Keep triggers on posting_snapshots and posting_brand_mentions where
they remain appropriate.

Revision ID: dd56e4f5a6b7
Revises: cc45d3e4f5a6
Create Date: 2026-02-18 11:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "dd56e4f5a6b7"
down_revision: str = "cc45d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_posting_enrichments_append_only ON posting_enrichments;")


def downgrade() -> None:
    op.execute("""
        CREATE TRIGGER trg_posting_enrichments_append_only
        BEFORE UPDATE OR DELETE ON posting_enrichments
        FOR EACH ROW
        EXECUTE FUNCTION enforce_append_only();
    """)
