"""update BDS and MarketSource scraper_config with category-specific search URLs

Revision ID: f8a9b0c1d2e3
Revises: b52ab5ef6cf1
Create Date: 2026-02-18 03:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8a9b0c1d2e3"
down_revision: str = "b52ab5ef6cf1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # BDS: expand from 2 unfiltered URLs to 7 category-specific URLs
    # Source: docs/competitor-careers.md
    # The dedup logic in _fetch_multi_url() handles cross-category overlaps.
    op.execute(
        sa.text("""
            UPDATE companies
            SET scraper_config = '{
                "search_urls": [
                    "https://careers-bdssolutions.icims.com/jobs/search?searchCategory=25262",
                    "https://careers-bdssolutions.icims.com/jobs/search?searchCategory=25261",
                    "https://careers-apolloretail.icims.com/jobs/search",
                    "https://careers-bdssolutions.icims.com/jobs/search?searchCategory=8721",
                    "https://careers-bdssolutions.icims.com/jobs/search?searchCategory=25265",
                    "https://careers-bdssolutions.icims.com/jobs/search?searchCategory=43894",
                    "https://careers-bdssolutions.icims.com/jobs/search?searchCategory=25264"
                ]
            }'::jsonb
            WHERE slug = 'bds'
        """)
    )

    # MarketSource: ensure both Field and Corporate portals are included
    # Source: docs/competitor-careers.md
    op.execute(
        sa.text("""
            UPDATE companies
            SET scraper_config = '{
                "search_urls": [
                    "https://applyatmarketsource-msc.icims.com/jobs/search",
                    "https://careers-marketsource.icims.com/jobs/search"
                ]
            }'::jsonb
            WHERE slug = 'marketsource'
        """)
    )


def downgrade() -> None:
    # Restore original unfiltered search URLs
    op.execute(
        sa.text("""
            UPDATE companies
            SET scraper_config = '{
                "search_urls": [
                    "https://careers-bdssolutions.icims.com/jobs/search",
                    "https://careers-apolloretail.icims.com/jobs/search"
                ]
            }'::jsonb
            WHERE slug = 'bds'
        """)
    )

    op.execute(
        sa.text("""
            UPDATE companies
            SET scraper_config = '{
                "search_urls": [
                    "https://applyatmarketsource-msc.icims.com/jobs/search",
                    "https://careers-marketsource.icims.com/jobs/search"
                ]
            }'::jsonb
            WHERE slug = 'marketsource'
        """)
    )
