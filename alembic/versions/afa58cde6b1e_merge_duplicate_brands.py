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

    # Drop append-only triggers that block UPDATE/DELETE on these tables.
    # These triggers are dropped permanently in a later migration (dd56e4f5a6b7),
    # but they must be absent here so the brand-merge DML can execute on a fresh DB
    # where migrations run in order and dd56e4f5a6b7 has not yet been applied.
    conn.execute(sa.text("DROP TRIGGER IF EXISTS enforce_append_only ON posting_brand_mentions"))
    conn.execute(sa.text("DROP TRIGGER IF EXISTS enforce_append_only ON posting_snapshots"))

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

    # Re-add the append-only triggers so the invariant is intact until
    # dd56e4f5a6b7 permanently drops them later in the migration chain.
    conn.execute(
        sa.text("""
            CREATE TRIGGER enforce_append_only
            BEFORE UPDATE OR DELETE ON posting_brand_mentions
            FOR EACH ROW EXECUTE FUNCTION prevent_update_delete()
        """)
    )
    conn.execute(
        sa.text("""
            CREATE TRIGGER enforce_append_only
            BEFORE UPDATE OR DELETE ON posting_snapshots
            FOR EACH ROW EXECUTE FUNCTION prevent_update_delete()
        """)
    )


def downgrade() -> None:
    pass
