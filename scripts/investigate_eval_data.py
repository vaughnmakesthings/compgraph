#!/usr/bin/env python3
"""Investigate Supabase instance. Run with: op run --env-file=.env -- uv run python scripts/investigate_eval_data.py"""

from __future__ import annotations

import asyncio

from sqlalchemy import func, select, text

from compgraph.db.session import async_session_factory
from compgraph.eval.models import EvalResult, EvalRun


async def main() -> None:
    async with async_session_factory() as session:
        # 0. Table row counts (public schema)
        print("=== Table row counts (public schema) ===")
        table_counts = await session.execute(
            text("""
                SELECT relname AS table_name, n_live_tup AS row_count
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                ORDER BY n_live_tup DESC
            """)
        )
        rows = table_counts.fetchall()
        total = sum(r.row_count for r in rows)
        for row in rows:
            pct = (row.row_count / total * 100) if total else 0
            print(f"  {row.table_name}: {row.row_count:,} ({pct:.1f}%)")
        print(f"  TOTAL: {total:,} rows across {len(rows)} tables\n")

        # 0b. Schema insights: tables by tier
        print("=== Tables by tier (CLAUDE.md) ===")
        dimension = ["companies", "brands", "retailers", "markets"]
        fact = ["postings", "posting_snapshots", "posting_enrichments", "posting_brand_mentions"]
        agg = [
            "agg_daily_velocity",
            "agg_brand_timeline",
            "agg_pay_benchmarks",
            "agg_posting_lifecycle",
        ]
        eval_t = [
            "eval_runs",
            "eval_results",
            "eval_corpus",
            "eval_comparisons",
            "eval_field_reviews",
        ]
        table_map = {r.table_name: r.row_count for r in rows}
        for tier, tables in [
            ("Dimension", dimension),
            ("Fact", fact),
            ("Aggregation", agg),
            ("Eval", eval_t),
        ]:
            counts = [table_map.get(t, 0) for t in tables]
            print(f"  {tier}: {sum(counts):,} total")
            for t, c in zip(tables, counts, strict=True):
                print(f"    - {t}: {c:,}")
        print()

        # 0c. Data freshness (per-table; column names vary)
        print("=== Data freshness (latest timestamp) ===")
        freshness_queries = [
            ("postings", "first_seen_at"),
            ("posting_snapshots", "created_at"),
            ("posting_enrichments", "enriched_at"),  # no created_at
            ("eval_runs", "created_at"),
        ]
        for tbl, col in freshness_queries:
            try:
                r = await session.execute(text(f"SELECT MAX({col}) AS latest FROM {tbl}"))  # noqa: S608
                row = r.fetchone()
                print(f"  {tbl}.{col}: {row.latest}")
            except Exception as e:
                await session.rollback()
                print(f"  {tbl}.{col}: (skip: {e})")
        print()

        # 1. Raw eval_runs
        print("=== eval_runs (raw) ===")
        result = await session.execute(
            select(EvalRun).order_by(EvalRun.created_at.desc()).limit(10)
        )
        runs = result.scalars().all()
        for r in runs:
            print(
                f"  id={r.id} pass={r.pass_number} model={r.model} "
                f"corpus_size={r.corpus_size} total_duration_ms={r.total_duration_ms} "
                f"created_at={r.created_at}"
            )
        print(f"  Total: {len(runs)} runs\n")

        # 2. Result counts per run
        print("=== eval_results count per run ===")
        stmt = select(EvalResult.run_id, func.count(EvalResult.id).label("cnt")).group_by(
            EvalResult.run_id
        )
        rows = (await session.execute(stmt)).all()
        for r in rows:
            print(f"  run_id={r.run_id} result_count={r.cnt}")
        print(f"  Total: {len(rows)} runs with results\n")

        # 3. Raw SQL to compare with API response shape
        print("=== Simulated API response (run + count) ===")
        run_ids = [r.id for r in runs]
        if run_ids:
            count_stmt = (
                select(EvalResult.run_id, func.count(EvalResult.id).label("cnt"))
                .where(EvalResult.run_id.in_(run_ids))
                .group_by(EvalResult.run_id)
            )
            count_rows = (await session.execute(count_stmt)).all()
            counts = {r.run_id: r.cnt for r in count_rows}
            for r in runs:
                cnt = counts.get(r.id, 0)
                status = (
                    "completed"
                    if r.total_duration_ms is not None
                    else ("running" if cnt > 0 else "starting")
                )
                print(
                    f"  id={r.id} status={status} total_items={r.corpus_size} completed_items={cnt}"
                )

        # 4. Check for anomalies
        print("\n=== Anomaly checks ===")
        null_corpus = await session.execute(select(EvalRun).where(EvalRun.corpus_size == 0))
        null_runs = null_corpus.scalars().all()
        if null_runs:
            print(f"  Runs with corpus_size=0: {len(null_runs)}")
        else:
            print("  No runs with corpus_size=0")

        # Check eval_results referencing non-existent runs
        orphan_stmt = text(
            """
            SELECT er.id, er.run_id FROM eval_results er
            LEFT JOIN eval_runs r ON er.run_id = r.id
            WHERE r.id IS NULL
            LIMIT 5
            """
        )
        orphan = await session.execute(orphan_stmt)
        orphan_rows = orphan.fetchall()
        if orphan_rows:
            print(f"  Orphan eval_results (run_id not in eval_runs): {len(orphan_rows)}")
        else:
            print("  No orphan eval_results")


if __name__ == "__main__":
    asyncio.run(main())
