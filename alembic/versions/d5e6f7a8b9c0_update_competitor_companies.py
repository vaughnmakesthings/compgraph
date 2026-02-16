"""update competitor companies: add 2020/BDS/MarketSource, drop Acosta/Advantage

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-02-16 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: str = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Delete dropped competitors (safety net — may not exist) ---
    # Delete dependent rows first, then companies
    op.execute(
        sa.text("""
            DELETE FROM posting_brand_mentions
            WHERE posting_id IN (
                SELECT p.id FROM postings p
                JOIN companies c ON p.company_id = c.id
                WHERE c.slug IN ('acosta', 'advantage')
            )
        """)
    )
    op.execute(
        sa.text("""
            DELETE FROM posting_enrichments
            WHERE posting_id IN (
                SELECT p.id FROM postings p
                JOIN companies c ON p.company_id = c.id
                WHERE c.slug IN ('acosta', 'advantage')
            )
        """)
    )
    op.execute(
        sa.text("""
            DELETE FROM posting_snapshots
            WHERE posting_id IN (
                SELECT p.id FROM postings p
                JOIN companies c ON p.company_id = c.id
                WHERE c.slug IN ('acosta', 'advantage')
            )
        """)
    )
    op.execute(
        sa.text("""
            DELETE FROM postings
            WHERE company_id IN (
                SELECT id FROM companies WHERE slug IN ('acosta', 'advantage')
            )
        """)
    )
    op.execute(
        sa.text("""
            DELETE FROM scrape_runs
            WHERE company_id IN (
                SELECT id FROM companies WHERE slug IN ('acosta', 'advantage')
            )
        """)
    )
    op.execute(sa.text("DELETE FROM companies WHERE slug IN ('acosta', 'advantage')"))

    # --- Insert new competitors ---

    # 2020 Companies (Workday CXS)
    op.execute(
        sa.text("""
            INSERT INTO companies (id, name, slug, ats_platform, career_site_url, scraper_config, created_at)
            VALUES (
                gen_random_uuid(),
                '2020 Companies',
                '2020',
                'workday',
                'https://2020companies.wd1.myworkdayjobs.com',
                '{"tenant": "2020companies", "site": "External_Careers"}'::jsonb,
                now()
            )
            ON CONFLICT (slug) DO NOTHING
        """)
    )

    # BDS Connected Solutions (iCIMS multi-URL — 2 portals, unfiltered)
    op.execute(
        sa.text("""
            INSERT INTO companies (id, name, slug, ats_platform, career_site_url, scraper_config, created_at)
            VALUES (
                gen_random_uuid(),
                'BDS Connected Solutions',
                'bds',
                'icims',
                'https://careers-bdssolutions.icims.com',
                '{"search_urls": ["https://careers-bdssolutions.icims.com/jobs/search", "https://careers-apolloretail.icims.com/jobs/search"]}'::jsonb,
                now()
            )
            ON CONFLICT (slug) DO NOTHING
        """)
    )

    # MarketSource (iCIMS multi-URL — Field + Corporate portals)
    op.execute(
        sa.text("""
            INSERT INTO companies (id, name, slug, ats_platform, career_site_url, scraper_config, created_at)
            VALUES (
                gen_random_uuid(),
                'MarketSource',
                'marketsource',
                'icims',
                'https://applyatmarketsource-msc.icims.com',
                '{"search_urls": ["https://applyatmarketsource-msc.icims.com/jobs/search", "https://careers-marketsource.icims.com/jobs/search"]}'::jsonb,
                now()
            )
            ON CONFLICT (slug) DO NOTHING
        """)
    )


def downgrade() -> None:
    # Delete dependent rows before companies to avoid FK violations
    op.execute(
        sa.text("""
            DELETE FROM posting_brand_mentions
            WHERE posting_id IN (
                SELECT p.id FROM postings p
                JOIN companies c ON p.company_id = c.id
                WHERE c.slug IN ('2020', 'bds', 'marketsource')
            )
        """)
    )
    op.execute(
        sa.text("""
            DELETE FROM posting_enrichments
            WHERE posting_id IN (
                SELECT p.id FROM postings p
                JOIN companies c ON p.company_id = c.id
                WHERE c.slug IN ('2020', 'bds', 'marketsource')
            )
        """)
    )
    op.execute(
        sa.text("""
            DELETE FROM posting_snapshots
            WHERE posting_id IN (
                SELECT p.id FROM postings p
                JOIN companies c ON p.company_id = c.id
                WHERE c.slug IN ('2020', 'bds', 'marketsource')
            )
        """)
    )
    op.execute(
        sa.text("""
            DELETE FROM postings
            WHERE company_id IN (
                SELECT id FROM companies WHERE slug IN ('2020', 'bds', 'marketsource')
            )
        """)
    )
    op.execute(
        sa.text("""
            DELETE FROM scrape_runs
            WHERE company_id IN (
                SELECT id FROM companies WHERE slug IN ('2020', 'bds', 'marketsource')
            )
        """)
    )
    op.execute(sa.text("DELETE FROM companies WHERE slug IN ('2020', 'bds', 'marketsource')"))
    # Note: Acosta/Advantage are not re-inserted on downgrade — they were broken
