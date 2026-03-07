#!/usr/bin/env python3
"""Generate eval/data/corpus.json from live postings for eval runs.

Usage:
  op run --env-file=.env -- uv run python scripts/generate_eval_corpus.py
  op run --env-file=.env -- uv run python scripts/generate_eval_corpus.py --limit 100 --company-slug bds

Output: eval/data/corpus.json (git-ignored)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from compgraph.config import Settings
from compgraph.db.models import Company, Posting, PostingSnapshot

CORPUS_MAX_TEXT_LENGTH = 10_000


def build_corpus_query(
    company_slug: str | None = None,
    limit: int = 200,
):
    latest_snapshot_date = (
        select(func.max(PostingSnapshot.snapshot_date))
        .where(PostingSnapshot.posting_id == Posting.id)
        .correlate(Posting)
        .scalar_subquery()
    )

    q = (
        select(Posting, PostingSnapshot, Company.slug)
        .join(
            PostingSnapshot,
            (PostingSnapshot.posting_id == Posting.id)
            & (PostingSnapshot.snapshot_date == latest_snapshot_date),
        )
        .join(Company, Company.id == Posting.company_id)
        .where(Posting.is_active.is_(True))
    )
    if company_slug:
        q = q.where(Company.slug == company_slug)
    return q.order_by(Posting.first_seen_at.desc()).limit(limit)


def rows_to_corpus(rows: list) -> list[dict]:
    corpus: list[dict] = []
    for posting, snapshot, slug in rows:
        corpus.append(
            {
                "id": f"posting_{posting.id}",
                "company_slug": slug,
                "title": snapshot.title_raw or "",
                "location": snapshot.location_raw or "",
                "full_text": (snapshot.full_text_raw or "")[:CORPUS_MAX_TEXT_LENGTH],
                "reference_pass1": None,
                "reference_pass2": None,
            }
        )
    return corpus


async def fetch_corpus(
    settings: Settings,
    company_slug: str | None = None,
    limit: int = 200,
) -> list[dict]:
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        connect_args={"ssl": "require"},
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as session:
            q = build_corpus_query(company_slug=company_slug, limit=limit)
            result = await session.execute(q)
            rows = result.all()
    finally:
        await engine.dispose()

    return rows_to_corpus(rows)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate eval corpus from postings")
    parser.add_argument("--limit", type=int, default=200, help="Max corpus size")
    parser.add_argument("--company-slug", type=str, help="Filter by company slug")
    args = parser.parse_args()

    settings = Settings()
    corpus_path = Path(__file__).parent.parent / "eval" / "data" / "corpus.json"
    corpus_path.parent.mkdir(parents=True, exist_ok=True)

    corpus = await fetch_corpus(
        settings,
        company_slug=args.company_slug,
        limit=args.limit,
    )

    if not corpus:
        print("WARNING: No active postings found. corpus.json will be empty.", file=sys.stderr)

    corpus_path.write_text(json.dumps(corpus, indent=2))
    print(f"Wrote {len(corpus)} items to {corpus_path}")


if __name__ == "__main__":
    asyncio.run(main())
