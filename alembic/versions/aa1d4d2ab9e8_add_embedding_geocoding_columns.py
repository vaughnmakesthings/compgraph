"""add embedding, latitude, longitude, h3_index columns for Phase 0 foundation

Revision ID: aa1d4d2ab9e8
Revises: d4e5f6a7b8c9
Create Date: 2026-03-06 18:00:00.000000

Adds pgvector embedding column to posting_enrichments for semantic search,
and geocoding columns (latitude, longitude, h3_index) to postings for
spatial queries.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "aa1d4d2ab9e8"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable pgvector extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Embeddings column on posting_enrichments
    op.add_column("posting_enrichments", sa.Column("embedding", Vector(384), nullable=True))

    # Geocoding columns on postings
    op.add_column("postings", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("postings", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("postings", sa.Column("h3_index", sa.String(15), nullable=True))

    # Partial index on h3_index (only non-null values)
    op.create_index(
        "idx_postings_h3",
        "postings",
        ["h3_index"],
        postgresql_where=sa.text("h3_index IS NOT NULL"),
    )

    # Note: HNSW index on embedding should be created AFTER backfill for performance.
    # Creating it on an empty column would be wasteful. Run a follow-up migration
    # after backfill_embeddings.py completes:
    #   CREATE INDEX idx_enrichments_embedding_hnsw
    #   ON posting_enrichments USING hnsw (embedding vector_cosine_ops)
    #   WITH (m = 16, ef_construction = 64);


def downgrade() -> None:
    op.drop_index("idx_postings_h3", table_name="postings")
    op.drop_column("postings", "h3_index")
    op.drop_column("postings", "longitude")
    op.drop_column("postings", "latitude")
    op.drop_column("posting_enrichments", "embedding")
