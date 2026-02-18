"""add append-only triggers to fact tables

Revision ID: bb47c2d3e4f5
Revises: aa88b1c2d3e4
Create Date: 2026-02-18 04:01:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "bb47c2d3e4f5"
down_revision: str = "aa88b1c2d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FACT_TABLES = ["posting_snapshots", "posting_enrichments", "posting_brand_mentions"]


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION enforce_append_only()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Table % is append-only. UPDATE and DELETE are not permitted.',
                TG_TABLE_NAME
                USING ERRCODE = 'restrict_violation';
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    for table in FACT_TABLES:
        op.execute(f"""
            CREATE TRIGGER trg_{table}_append_only
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION enforce_append_only();
        """)


def downgrade() -> None:
    for table in FACT_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_append_only ON {table};")
    op.execute("DROP FUNCTION IF EXISTS enforce_append_only();")
