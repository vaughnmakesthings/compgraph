"""seed T-ROC company (Workday CXS)

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6, a7908299a887
Create Date: 2026-02-15 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: tuple[str, str] = ("a1b2c3d4e5f6", "a7908299a887")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text("""
            INSERT INTO companies (id, name, slug, ats_platform, career_site_url, scraper_config, created_at)
            VALUES (
                gen_random_uuid(),
                'T-ROC',
                'troc',
                'workday',
                'https://troc.wd501.myworkdayjobs.com',
                '{"tenant": "troc", "site": "TROC_External"}'::jsonb,
                now()
            )
            ON CONFLICT DO NOTHING
        """)
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM companies WHERE slug = 'troc'"))
