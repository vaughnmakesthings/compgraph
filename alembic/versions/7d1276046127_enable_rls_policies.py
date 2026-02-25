"""enable RLS policies for all public tables

Revision ID: 7d1276046127
Revises: c3d4e5f6a7b8
Create Date: 2026-02-25 22:00:00.000000

Enables Row Level Security on all 23 public-schema tables and creates
policies for 3-tier access: viewer (authenticated SELECT), admin
(authenticated + role check), service_role (bypasses RLS automatically).

Access model:
  - anon: no access (invite-only app)
  - authenticated/viewer: SELECT on all tables, own-row on users
  - authenticated/admin: SELECT on all + write eval + manage users
  - service_role: bypasses RLS (Supabase built-in), no policies needed

Performance notes:
  - Admin check uses a SECURITY DEFINER function (public.is_admin())
    to avoid row-level subquery overhead and enable initPlan caching.
  - auth.uid() wrapped in (SELECT auth.uid()) for initPlan caching
    (evaluated once per statement, not once per row).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7d1276046127"
down_revision: str = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ---------------------------------------------------------------------------
# Table groupings
# ---------------------------------------------------------------------------

DIMENSION_TABLES = ["companies", "brands", "retailers", "markets"]

FACT_TABLES = [
    "postings",
    "posting_snapshots",
    "posting_enrichments",
    "posting_brand_mentions",
]

AGGREGATION_TABLES = [
    "agg_daily_velocity",
    "agg_brand_timeline",
    "agg_pay_benchmarks",
    "agg_posting_lifecycle",
    "agg_brand_churn_signals",
    "agg_market_coverage_gaps",
    "agg_brand_agency_overlap",
]

RUN_TABLES = ["scrape_runs", "enrichment_runs"]

EVAL_TABLES = [
    "eval_corpus",
    "eval_runs",
    "eval_results",
    "eval_comparisons",
    "eval_field_reviews",
]

LOCATION_TABLES = ["location_mappings"]

ALL_TABLES = (
    DIMENSION_TABLES
    + FACT_TABLES
    + AGGREGATION_TABLES
    + RUN_TABLES
    + EVAL_TABLES
    + LOCATION_TABLES
    + ["users"]
)

# ---------------------------------------------------------------------------
# Read-only tables (viewer = SELECT, admin = SELECT, service_role bypasses)
# ---------------------------------------------------------------------------

READONLY_TABLES = DIMENSION_TABLES + FACT_TABLES + AGGREGATION_TABLES + RUN_TABLES + LOCATION_TABLES

# Admin role check — SECURITY DEFINER function for performance + initPlan caching
ADMIN_CHECK = "public.is_admin()"


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 0. Create SECURITY DEFINER helper for admin check
    # ------------------------------------------------------------------
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION public.is_admin()
            RETURNS boolean
            LANGUAGE sql
            STABLE
            SECURITY DEFINER
            SET search_path = ''
            AS $$
                SELECT EXISTS (
                    SELECT 1 FROM public.users
                    WHERE auth_uid = (SELECT auth.uid())
                      AND role = 'admin'
                )
            $$
            """
        )
    )

    # ------------------------------------------------------------------
    # 1. Enable RLS on every table
    # ------------------------------------------------------------------
    for table in ALL_TABLES:
        op.execute(sa.text(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY"))

    # ------------------------------------------------------------------
    # 2. Revoke default public/anon access (defense in depth)
    # ------------------------------------------------------------------
    for table in ALL_TABLES:
        op.execute(sa.text(f"REVOKE ALL ON public.{table} FROM anon"))

    # ------------------------------------------------------------------
    # 3. Read-only tables: authenticated users can SELECT
    # ------------------------------------------------------------------
    for table in READONLY_TABLES:
        op.execute(
            sa.text(
                f"CREATE POLICY authenticated_select ON public.{table} "
                f"FOR SELECT TO authenticated USING (true)"
            )
        )

    # ------------------------------------------------------------------
    # 4. Eval tables: authenticated SELECT + admin write
    # ------------------------------------------------------------------
    for table in EVAL_TABLES:
        op.execute(
            sa.text(
                f"CREATE POLICY authenticated_select ON public.{table} "
                f"FOR SELECT TO authenticated USING (true)"
            )
        )
        op.execute(
            sa.text(
                f"CREATE POLICY admin_write ON public.{table} "
                f"FOR INSERT TO authenticated "
                f"WITH CHECK ({ADMIN_CHECK})"
            )
        )
        op.execute(
            sa.text(
                f"CREATE POLICY admin_update ON public.{table} "
                f"FOR UPDATE TO authenticated "
                f"USING ({ADMIN_CHECK})"
            )
        )

    # ------------------------------------------------------------------
    # 5. Users table: own-row SELECT for viewers, full access for admins
    # ------------------------------------------------------------------
    op.execute(
        sa.text(
            "CREATE POLICY users_select_own ON public.users "
            "FOR SELECT TO authenticated "
            "USING (auth_uid = (SELECT auth.uid()))"
        )
    )

    op.execute(
        sa.text(
            f"CREATE POLICY users_admin_select ON public.users "
            f"FOR SELECT TO authenticated "
            f"USING ({ADMIN_CHECK})"
        )
    )

    op.execute(
        sa.text(
            f"CREATE POLICY users_admin_update ON public.users "
            f"FOR UPDATE TO authenticated "
            f"USING ({ADMIN_CHECK})"
        )
    )

    op.execute(
        sa.text(
            f"CREATE POLICY users_admin_insert ON public.users "
            f"FOR INSERT TO authenticated "
            f"WITH CHECK ({ADMIN_CHECK})"
        )
    )


def downgrade() -> None:
    # ------------------------------------------------------------------
    # Drop all policies (name-based, idempotent via IF EXISTS)
    # ------------------------------------------------------------------

    # Read-only tables
    for table in READONLY_TABLES:
        op.execute(sa.text(f"DROP POLICY IF EXISTS authenticated_select ON public.{table}"))

    # Eval tables
    for table in EVAL_TABLES:
        op.execute(sa.text(f"DROP POLICY IF EXISTS authenticated_select ON public.{table}"))
        op.execute(sa.text(f"DROP POLICY IF EXISTS admin_write ON public.{table}"))
        op.execute(sa.text(f"DROP POLICY IF EXISTS admin_update ON public.{table}"))

    # Users table
    op.execute(sa.text("DROP POLICY IF EXISTS users_select_own ON public.users"))
    op.execute(sa.text("DROP POLICY IF EXISTS users_admin_select ON public.users"))
    op.execute(sa.text("DROP POLICY IF EXISTS users_admin_update ON public.users"))
    op.execute(sa.text("DROP POLICY IF EXISTS users_admin_insert ON public.users"))

    # ------------------------------------------------------------------
    # Drop SECURITY DEFINER helper function
    # ------------------------------------------------------------------
    op.execute(sa.text("DROP FUNCTION IF EXISTS public.is_admin()"))

    # ------------------------------------------------------------------
    # Disable RLS on all tables
    # ------------------------------------------------------------------
    for table in ALL_TABLES:
        op.execute(sa.text(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY"))

    # ------------------------------------------------------------------
    # Re-grant anon access (restore Supabase defaults)
    # ------------------------------------------------------------------
    for table in ALL_TABLES:
        op.execute(sa.text(f"GRANT ALL ON public.{table} TO anon"))
