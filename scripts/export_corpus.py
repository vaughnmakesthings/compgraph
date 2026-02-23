"""Export postings from CompGraph Supabase DB to local corpus.json.

Usage:
    cd compgraph-eval
    op run --env-file=../.env -- uv run python scripts/export_corpus.py --limit 100

Requires [export] optional dependencies: asyncpg, sqlalchemy[asyncio]
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


async def export(database_url: str, output_path: str, limit: int) -> None:
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        query = text("""
            SELECT
                p.id::text as id,
                c.slug as company_slug,
                ps.title_raw as title,
                ps.location_raw as location,
                ps.full_text_raw as full_text,
                jsonb_build_object(
                    'role_archetype', pe.role_archetype,
                    'role_level', pe.role_level,
                    'employment_type', pe.employment_type,
                    'pay_type', pe.pay_type,
                    'pay_min', pe.pay_min,
                    'pay_max', pe.pay_max,
                    'pay_frequency', pe.pay_frequency,
                    'commission_mentioned', pe.commission_mentioned,
                    'benefits_mentioned', pe.benefits_mentioned,
                    'content_role_specific', pe.content_role_specific
                ) as reference_pass1
            FROM postings p
            JOIN companies c ON p.company_id = c.id
            JOIN LATERAL (
                SELECT ps2.title_raw, ps2.location_raw, ps2.full_text_raw
                FROM posting_snapshots ps2
                WHERE ps2.posting_id = p.id
                ORDER BY ps2.snapshot_date DESC
                LIMIT 1
            ) ps ON true
            LEFT JOIN posting_enrichments pe ON p.id = pe.posting_id
            WHERE ps.full_text_raw IS NOT NULL
              AND length(ps.full_text_raw) > 100
            ORDER BY random()
            LIMIT :limit
        """)
        result = await session.execute(query, {"limit": limit})
        rows = result.mappings().all()

    postings = []
    for row in rows:
        posting = {
            "id": row["id"],
            "company_slug": row["company_slug"],
            "title": row["title"],
            "location": row["location"],
            "full_text": row["full_text"],
            "reference_pass1": dict(row["reference_pass1"])
            if row["reference_pass1"]
            else None,
        }
        postings.append(posting)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(postings, indent=2))
    print(f"Exported {len(postings)} postings to {output_path}")

    await engine.dispose()


def main():
    import os

    parser = argparse.ArgumentParser(description="Export postings to corpus.json")
    parser.add_argument("--limit", type=int, default=100, help="Number of postings")
    parser.add_argument("--output", default="data/corpus.json", help="Output path")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set. Use: op run --env-file=../.env --")
        raise SystemExit(1)

    # Ensure asyncpg dialect for SQLAlchemy async engine (handles postgres:// and postgresql://)
    if database_url.startswith("postgresql://"):
        database_url = "postgresql+asyncpg://" + database_url[len("postgresql://") :]
    elif database_url.startswith("postgres://"):
        database_url = "postgresql+asyncpg://" + database_url[len("postgres://") :]

    asyncio.run(export(database_url, args.output, args.limit))


if __name__ == "__main__":
    main()
