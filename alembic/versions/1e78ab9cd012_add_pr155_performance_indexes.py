"""add pr155 performance indexes

Revision ID: 1e78ab9cd012
Revises: 2109fd94f37f
Create Date: 2026-02-22 22:30:00.000000

Adds the 7 indexes introduced in models.py by PR #155 (tier 2 bug fixes).
Uses CREATE INDEX IF NOT EXISTS to be idempotent — PostingEnrichment indexes
(brand_id, retailer_id, market_id) already have partial coverage under plural
names (ix_posting_enrichments_*) from migration cc45d3e4f5a6; the singular
names match the current model __table_args__ declarations.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1e78ab9cd012"
down_revision: str | None = "2109fd94f37f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (index_name, table_name, columns)
INDEXES = [
    (
        "ix_posting_enrichment_posting_version",
        "posting_enrichments",
        "posting_id, enrichment_version",
    ),
    ("ix_posting_enrichment_brand_id", "posting_enrichments", "brand_id"),
    ("ix_posting_enrichment_retailer_id", "posting_enrichments", "retailer_id"),
    ("ix_posting_enrichment_market_id", "posting_enrichments", "market_id"),
    (
        "ix_posting_brand_mention_posting_entity",
        "posting_brand_mentions",
        "posting_id, entity_type",
    ),
    (
        "ix_agg_pay_benchmarks_company_role",
        "agg_pay_benchmarks",
        "company_id, role_archetype",
    ),
    (
        "ix_agg_posting_lifecycle_company_period",
        "agg_posting_lifecycle",
        "company_id, period",
    ),
]


def upgrade() -> None:
    for name, table, columns in INDEXES:
        op.execute(sa.text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns})"))


def downgrade() -> None:
    for name, _table, _columns in reversed(INDEXES):
        op.execute(sa.text(f"DROP INDEX IF EXISTS {name}"))
