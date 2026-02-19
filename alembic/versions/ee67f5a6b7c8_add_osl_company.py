"""add OSL Retail Services as 5th competitor (iCIMS, 2 English portals)

OSL uses iCIMS with US and Canada EN portals. The existing iCIMS adapter
handles multi-portal scraping via scraper_config.search_urls.

Closes: #125

Revision ID: ee67f5a6b7c8
Revises: dd56e4f5a6b7
Create Date: 2026-02-19 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ee67f5a6b7c8"
down_revision: str = "dd56e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text("""
            INSERT INTO companies (id, name, slug, ats_platform, career_site_url, scraper_config, created_at)
            VALUES (
                gen_random_uuid(),
                'OSL Retail Services',
                'osl',
                'icims',
                'https://uscareers-oslrs.icims.com',
                '{"search_urls": ["https://uscareers-oslrs.icims.com/jobs/search", "https://canadaengcareers-oslrs.icims.com/jobs/search"]}'::jsonb,
                now()
            )
            ON CONFLICT (slug) DO UPDATE SET
                career_site_url = EXCLUDED.career_site_url,
                scraper_config = EXCLUDED.scraper_config
        """)
    )


def downgrade() -> None:
    # Delete in FK-safe order: deepest dependents first
    op.execute(
        sa.text("""
            DELETE FROM posting_brand_mentions
            WHERE posting_id IN (
                SELECT p.id FROM postings p
                JOIN companies c ON p.company_id = c.id
                WHERE c.slug = 'osl'
            )
        """)
    )
    op.execute(
        sa.text("""
            DELETE FROM posting_enrichments
            WHERE posting_id IN (
                SELECT p.id FROM postings p
                JOIN companies c ON p.company_id = c.id
                WHERE c.slug = 'osl'
            )
        """)
    )
    op.execute(
        sa.text("""
            DELETE FROM posting_snapshots
            WHERE posting_id IN (
                SELECT p.id FROM postings p
                JOIN companies c ON p.company_id = c.id
                WHERE c.slug = 'osl'
            )
        """)
    )
    op.execute(
        sa.text("""
            DELETE FROM postings
            WHERE company_id IN (
                SELECT id FROM companies WHERE slug = 'osl'
            )
        """)
    )
    op.execute(
        sa.text("""
            DELETE FROM scrape_runs
            WHERE company_id IN (
                SELECT id FROM companies WHERE slug = 'osl'
            )
        """)
    )
    # Aggregation tables also have company_id FK (non-cascading)
    for agg_table in [
        "agg_daily_velocity",
        "agg_brand_timeline",
        "agg_pay_benchmarks",
        "agg_posting_lifecycle",
    ]:
        op.execute(
            sa.text(f"""
                DELETE FROM {agg_table}
                WHERE company_id IN (
                    SELECT id FROM companies WHERE slug = 'osl'
                )
            """)
        )
    op.execute(sa.text("DELETE FROM companies WHERE slug = 'osl'"))
