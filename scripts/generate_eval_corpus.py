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
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from compgraph.config import Settings
from compgraph.db.models import Company, Posting, PostingSnapshot


async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate eval corpus from postings")
    parser.add_argument("--limit", type=int, default=200, help="Max corpus size")
    parser.add_argument("--company-slug", type=str, help="Filter by company slug")
    args = parser.parse_args()

    settings = Settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    corpus_path = Path(__file__).parent.parent / "eval" / "data" / "corpus.json"
    corpus_path.parent.mkdir(parents=True, exist_ok=True)

    latest_snapshot_date = (
        select(func.max(PostingSnapshot.snapshot_date))
        .where(PostingSnapshot.posting_id == Posting.id)
        .correlate(Posting)
        .scalar_subquery()
    )

    async with async_session() as session:
        q = (
            select(Posting, PostingSnapshot, Company.slug)
            .join(
                PostingSnapshot,
                (PostingSnapshot.posting_id == Posting.id)
                & (PostingSnapshot.snapshot_date == latest_snapshot_date),
            )
            .join(Company, Company.id == Posting.company_id)
            .where(Posting.is_active)
        )
        if args.company_slug:
            q = q.where(Company.slug == args.company_slug)
        q = q.order_by(Posting.first_seen_at.desc()).limit(args.limit)
        result = await session.execute(q)
        rows = result.all()

    corpus = []
    for posting, snapshot, slug in rows:
        corpus.append(
            {
                "id": f"posting_{posting.id}",
                "company_slug": slug,
                "title": snapshot.title_raw or "",
                "location": snapshot.location_raw or "",
                "full_text": (snapshot.full_text_raw or "")[:10000],
                "reference_pass1": None,
                "reference_pass2": None,
            }
        )

    corpus_path.write_text(json.dumps(corpus, indent=2))
    print(f"Wrote {len(corpus)} items to {corpus_path}")


if __name__ == "__main__":
    asyncio.run(main())
