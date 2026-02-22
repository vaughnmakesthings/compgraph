"""merge duplicate brands

Revision ID: afa58cde6b1e
Revises: ac20bd3de6fd
Create Date: 2026-02-22 00:18:50.800660

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "afa58cde6b1e"
down_revision: str | None = "ac20bd3de6fd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DUPLICATE_PAIRS = [
    ("Reliant", "Reliant Energy"),
    ("LG", "LG Electronics"),
    ("Virgin Mobile", "Virgin Plus"),
]


def upgrade() -> None:
    conn = op.get_bind()

    for dup_name, canonical_name in DUPLICATE_PAIRS:
        dup_row = conn.execute(
            sa.text("SELECT id FROM brands WHERE name = :name"),
            {"name": dup_name},
        ).fetchone()

        canonical_row = conn.execute(
            sa.text("SELECT id FROM brands WHERE name = :name"),
            {"name": canonical_name},
        ).fetchone()

        if dup_row is None or canonical_row is None:
            continue

        dup_id = dup_row[0]
        canonical_id = canonical_row[0]

        conn.execute(
            sa.text(
                "UPDATE posting_brand_mentions "
                "SET resolved_brand_id = :canonical_id "
                "WHERE resolved_brand_id = :dup_id"
            ),
            {"canonical_id": canonical_id, "dup_id": dup_id},
        )

        conn.execute(
            sa.text(
                "UPDATE posting_enrichments SET brand_id = :canonical_id WHERE brand_id = :dup_id"
            ),
            {"canonical_id": canonical_id, "dup_id": dup_id},
        )

        conn.execute(
            sa.text("DELETE FROM brands WHERE id = :dup_id"),
            {"dup_id": dup_id},
        )


def downgrade() -> None:
    pass
