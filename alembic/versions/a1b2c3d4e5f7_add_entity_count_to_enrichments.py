"""Add entity_count to posting_enrichments.

Revision ID: a1b2c3d4e5f7
Revises: 7d1276046127
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f7"
down_revision = "7d1276046127"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "posting_enrichments",
        sa.Column("entity_count", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "check_entity_count_non_negative",
        "posting_enrichments",
        "entity_count IS NULL OR entity_count >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("check_entity_count_non_negative", "posting_enrichments", type_="check")
    op.drop_column("posting_enrichments", "entity_count")
