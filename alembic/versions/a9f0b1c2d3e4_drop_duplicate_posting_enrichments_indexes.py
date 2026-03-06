"""drop duplicate posting_enrichments indexes

Revision ID: a9f0b1c2d3e4
Revises: 7d1276046127
Create Date: 2026-03-05 12:00:00.000000

Migration cc45d3e4f5a6 created plural-named indexes on posting_enrichments
(ix_posting_enrichments_brand_id, etc.). Migration 1e78ab9cd012 later created
singular-named equivalents (ix_posting_enrichment_brand_id, etc.) to match the
current model __table_args__ declarations. Both sets now coexist, doubling write
overhead on every INSERT/UPDATE to posting_enrichments. This migration drops the
older plural-named duplicates.

Affected indexes (dropping):
- ix_posting_enrichments_brand_id    → replaced by ix_posting_enrichment_brand_id
- ix_posting_enrichments_retailer_id → replaced by ix_posting_enrichment_retailer_id
- ix_posting_enrichments_market_id   → replaced by ix_posting_enrichment_market_id
- ix_posting_enrichments_posting_id  → replaced by ix_posting_enrichment_posting_version
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a9f0b1c2d3e4"
down_revision: str | None = "7d1276046127"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (index_name, table_name, column) — plural-named duplicates to drop
DUPLICATE_INDEXES = [
    ("ix_posting_enrichments_brand_id", "posting_enrichments", "brand_id"),
    ("ix_posting_enrichments_retailer_id", "posting_enrichments", "retailer_id"),
    ("ix_posting_enrichments_market_id", "posting_enrichments", "market_id"),
    ("ix_posting_enrichments_posting_id", "posting_enrichments", "posting_id"),
]


def upgrade() -> None:
    for name, _table, _column in DUPLICATE_INDEXES:
        op.execute(sa.text(f"DROP INDEX IF EXISTS {name}"))


def downgrade() -> None:
    for name, table, column in reversed(DUPLICATE_INDEXES):
        op.execute(sa.text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({column})"))
