"""add eval tables

Revision ID: b2c3d4e5f6a7
Revises: 1e78ab9cd012
Create Date: 2026-02-22 23:00:00.000000

Creates 5 eval tables (eval_corpus, eval_runs, eval_results, eval_comparisons,
eval_field_reviews) ported from the SQLite schema in eval/eval/store.py.
Uses CREATE TABLE IF NOT EXISTS throughout for idempotency.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "1e78ab9cd012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS eval_corpus (
                id          TEXT PRIMARY KEY,
                company_slug TEXT NOT NULL,
                title       TEXT NOT NULL,
                location    TEXT,
                full_text   TEXT NOT NULL,
                reference_pass1 JSONB,
                reference_pass2 JSONB
            )
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS eval_runs (
                id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                pass_number         INTEGER NOT NULL CHECK (pass_number IN (1, 2)),
                model               TEXT NOT NULL,
                prompt_version      TEXT NOT NULL,
                corpus_size         INTEGER NOT NULL DEFAULT 0,
                total_input_tokens  INTEGER,
                total_output_tokens INTEGER,
                total_cost_usd      DOUBLE PRECISION,
                total_duration_ms   INTEGER,
                created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS eval_results (
                id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                run_id        UUID NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
                posting_id    TEXT NOT NULL REFERENCES eval_corpus(id),
                raw_response  TEXT,
                parsed_result JSONB,
                parse_success BOOLEAN NOT NULL,
                input_tokens  INTEGER,
                output_tokens INTEGER,
                cost_usd      DOUBLE PRECISION,
                latency_ms    INTEGER,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (run_id, posting_id)
            )
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS eval_comparisons (
                id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                posting_id   TEXT NOT NULL REFERENCES eval_corpus(id),
                result_a_id  UUID NOT NULL REFERENCES eval_results(id) ON DELETE CASCADE,
                result_b_id  UUID NOT NULL REFERENCES eval_results(id) ON DELETE CASCADE,
                winner       TEXT NOT NULL CHECK (winner IN ('a', 'b', 'tie', 'both_bad')),
                notes        TEXT,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS eval_field_reviews (
                id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                result_id     UUID NOT NULL REFERENCES eval_results(id) ON DELETE CASCADE,
                field_name    TEXT NOT NULL,
                model_value   TEXT,
                is_correct    INTEGER NOT NULL,
                correct_value TEXT,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (result_id, field_name)
            )
            """
        )
    )

    # Indexes
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_eval_runs_pass_model ON eval_runs (pass_number, model)"
        )
    )
    op.execute(
        sa.text("CREATE INDEX IF NOT EXISTS ix_eval_results_run_id ON eval_results (run_id)")
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_eval_comparisons_posting_id ON eval_comparisons (posting_id)"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_eval_field_reviews_result_id ON eval_field_reviews (result_id)"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS eval_field_reviews"))
    op.execute(sa.text("DROP TABLE IF EXISTS eval_comparisons"))
    op.execute(sa.text("DROP TABLE IF EXISTS eval_results"))
    op.execute(sa.text("DROP TABLE IF EXISTS eval_runs"))
    op.execute(sa.text("DROP TABLE IF EXISTS eval_corpus"))
