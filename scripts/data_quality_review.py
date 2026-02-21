#!/usr/bin/env python3
"""Data quality review for enrichment pipeline — M3 exit criterion.

Runs 6 SQL checks against the database and prints a structured report
with WARN/OK status per check.

Usage:
    op run --env-file=.env -- uv run python scripts/data_quality_review.py
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("data_quality")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrichment data quality review")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed query results")
    return parser.parse_args()


async def run_checks(*, verbose: bool = False) -> int:
    """Run all data quality checks. Returns count of warnings."""
    from sqlalchemy import distinct, func, literal_column, select, text

    from compgraph.db.models import (
        Brand,
        Company,
        Posting,
        PostingBrandMention,
        PostingEnrichment,
    )
    from compgraph.db.session import async_session_factory

    warnings = 0

    async with async_session_factory() as session:
        # ------------------------------------------------------------------
        # Check 1: Pass 1/2 completion rates per company
        # ------------------------------------------------------------------
        print("\n" + "=" * 70)
        print("CHECK 1: Enrichment Completion Rates by Company")
        print("=" * 70)

        total_stmt = (
            select(
                Company.name.label("company"),
                func.count(distinct(Posting.id)).label("total_postings"),
            )
            .join(Posting, Company.id == Posting.company_id)
            .where(Posting.is_active.is_(True))
            .group_by(Company.name)
            .order_by(Company.name)
        )
        total_result = await session.execute(total_stmt)
        totals = {row.company: row.total_postings for row in total_result}

        enriched_stmt = (
            select(
                Company.name.label("company"),
                func.count(distinct(Posting.id)).label("enriched"),
            )
            .join(Posting, Company.id == Posting.company_id)
            .join(PostingEnrichment, Posting.id == PostingEnrichment.posting_id)
            .where(Posting.is_active.is_(True))
            .group_by(Company.name)
        )
        enriched_result = await session.execute(enriched_stmt)
        enriched = {row.company: row.enriched for row in enriched_result}

        pass2_stmt = (
            select(
                Company.name.label("company"),
                func.count(distinct(Posting.id)).label("pass2_done"),
            )
            .join(Posting, Company.id == Posting.company_id)
            .join(PostingEnrichment, Posting.id == PostingEnrichment.posting_id)
            .where(Posting.is_active.is_(True))
            .where(PostingEnrichment.enrichment_version.like("%pass2%"))
            .group_by(Company.name)
        )
        pass2_result = await session.execute(pass2_stmt)
        pass2 = {row.company: row.pass2_done for row in pass2_result}

        for company, total in sorted(totals.items()):
            p1 = enriched.get(company, 0)
            p2 = pass2.get(company, 0)
            p1_pct = (p1 / total * 100) if total else 0
            p2_pct = (p2 / total * 100) if total else 0
            status = "WARN" if p2_pct < 90 else "OK"
            if status == "WARN":
                warnings += 1
            print(
                f"  [{status}] {company}: {total} postings, "
                f"Pass 1: {p1} ({p1_pct:.0f}%), Pass 2: {p2} ({p2_pct:.0f}%)"
            )

        # ------------------------------------------------------------------
        # Check 2: Duplicate brand mentions (damage from #102)
        # ------------------------------------------------------------------
        print("\n" + "=" * 70)
        print("CHECK 2: Duplicate Brand Mentions")
        print("=" * 70)

        dup_stmt = (
            select(
                PostingBrandMention.posting_id,
                PostingBrandMention.entity_name,
                func.count().label("cnt"),
            )
            .group_by(PostingBrandMention.posting_id, PostingBrandMention.entity_name)
            .having(func.count() > 1)
        )
        dup_result = await session.execute(dup_stmt)
        dups = dup_result.all()

        if dups:
            warnings += 1
            print(f"  [WARN] {len(dups)} posting/entity pairs have duplicate mentions")
            if verbose:
                for row in dups[:20]:
                    print(f"    posting={row.posting_id} entity={row.entity_name} count={row.cnt}")
        else:
            print("  [OK] No duplicate brand mentions found")

        # ------------------------------------------------------------------
        # Check 3: Brand-less fingerprints (damage from #105)
        # ------------------------------------------------------------------
        print("\n" + "=" * 70)
        print("CHECK 3: Brand-less Fingerprints")
        print("=" * 70)

        brandless_stmt = (
            select(func.count())
            .select_from(Posting)
            .join(PostingEnrichment, Posting.id == PostingEnrichment.posting_id)
            .where(Posting.fingerprint_hash.isnot(None))
            .where(PostingEnrichment.brand_id.is_(None))
            .where(PostingEnrichment.enrichment_version.like("%pass2%"))
        )
        brandless_result = await session.execute(brandless_stmt)
        brandless_count = brandless_result.scalar() or 0

        total_fp_stmt = (
            select(func.count()).select_from(Posting).where(Posting.fingerprint_hash.isnot(None))
        )
        total_fp_result = await session.execute(total_fp_stmt)
        total_fp = total_fp_result.scalar() or 0

        if brandless_count > 0:
            warnings += 1
            print(
                f"  [WARN] {brandless_count}/{total_fp} fingerprinted postings "
                f"have no brand_id (Pass 2 complete but no brand resolved)"
            )
        else:
            print(f"  [OK] All {total_fp} fingerprinted postings have brand_id or pre-Pass 2")

        # ------------------------------------------------------------------
        # Check 4: Pay extraction coverage + plausibility
        # ------------------------------------------------------------------
        print("\n" + "=" * 70)
        print("CHECK 4: Pay Extraction Coverage & Plausibility")
        print("=" * 70)

        pay_stmt = (
            select(
                PostingEnrichment.role_archetype,
                func.count().label("total"),
                func.count(PostingEnrichment.pay_min).label("with_pay"),
                func.min(PostingEnrichment.pay_min).label("min_pay"),
                func.max(PostingEnrichment.pay_max).label("max_pay"),
                func.avg(PostingEnrichment.pay_min).label("avg_min"),
            )
            .join(Posting, Posting.id == PostingEnrichment.posting_id)
            .where(Posting.is_active.is_(True))
            .where(PostingEnrichment.pay_frequency == "hour")
            .group_by(PostingEnrichment.role_archetype)
            .order_by(literal_column("total").desc())
        )
        pay_result = await session.execute(pay_stmt)
        pay_rows = pay_result.all()

        for row in pay_rows:
            issues = []
            if row.min_pay is not None and row.min_pay < 5:
                issues.append(f"min=${row.min_pay:.2f}<$5")
            if row.max_pay is not None and row.max_pay > 200:
                issues.append(f"max=${row.max_pay:.2f}>$200")
            status = "WARN" if issues else "OK"
            if issues:
                warnings += 1
            pct = (row.with_pay / row.total * 100) if row.total else 0
            avg_str = f"${row.avg_min:.2f}" if row.avg_min else "N/A"
            print(
                f"  [{status}] {row.role_archetype or 'null'}: "
                f"{row.with_pay}/{row.total} with hourly pay ({pct:.0f}%), "
                f"avg_min={avg_str}" + (f" — {', '.join(issues)}" if issues else "")
            )

        # Also check non-hourly
        no_pay_stmt = (
            select(func.count())
            .select_from(PostingEnrichment)
            .join(Posting, Posting.id == PostingEnrichment.posting_id)
            .where(Posting.is_active.is_(True))
            .where(PostingEnrichment.pay_min.is_(None))
            .where(PostingEnrichment.pay_max.is_(None))
        )
        no_pay_result = await session.execute(no_pay_stmt)
        no_pay_count = no_pay_result.scalar() or 0
        total_enriched_stmt = (
            select(func.count())
            .select_from(PostingEnrichment)
            .join(Posting, Posting.id == PostingEnrichment.posting_id)
            .where(Posting.is_active.is_(True))
        )
        total_enriched_result = await session.execute(total_enriched_stmt)
        total_enriched = total_enriched_result.scalar() or 0
        if total_enriched:
            pct_no_pay = no_pay_count / total_enriched * 100
            print(f"  [INFO] {no_pay_count}/{total_enriched} ({pct_no_pay:.0f}%) have no pay data")

        # ------------------------------------------------------------------
        # Check 5: Role archetype distribution
        # ------------------------------------------------------------------
        print("\n" + "=" * 70)
        print("CHECK 5: Role Archetype Distribution")
        print("=" * 70)

        arch_stmt = (
            select(
                PostingEnrichment.role_archetype,
                func.count().label("cnt"),
            )
            .join(Posting, Posting.id == PostingEnrichment.posting_id)
            .where(Posting.is_active.is_(True))
            .group_by(PostingEnrichment.role_archetype)
            .order_by(literal_column("cnt").desc())
        )
        arch_result = await session.execute(arch_stmt)
        arch_rows = arch_result.all()
        total_arch = sum(row.cnt for row in arch_rows) if arch_rows else 0

        other_count = 0
        for row in arch_rows:
            pct = (row.cnt / total_arch * 100) if total_arch else 0
            label = row.role_archetype or "null"
            print(f"  {label}: {row.cnt} ({pct:.0f}%)")
            if label == "other":
                other_count = row.cnt

        if total_arch and (other_count / total_arch * 100) > 50:
            warnings += 1
            print('  [WARN] "other" archetype exceeds 50% — prompt may need tuning')
        else:
            print("  [OK] Archetype distribution looks reasonable")

        # ------------------------------------------------------------------
        # Check 6: Unresolved entity names (top 30 by frequency)
        # ------------------------------------------------------------------
        print("\n" + "=" * 70)
        print("CHECK 6: Unresolved Entity Names (no brand/retailer match)")
        print("=" * 70)

        # Entity mentions where both brand_id and retailer_id are NULL
        # on the enrichment record (i.e., entity was mentioned but not resolved
        # to a known brand/retailer)
        unresolved_stmt = (
            select(
                PostingBrandMention.entity_name,
                PostingBrandMention.entity_type,
                func.count().label("cnt"),
            )
            .where(PostingBrandMention.resolved_brand_id.is_(None))
            .where(PostingBrandMention.resolved_retailer_id.is_(None))
            .group_by(PostingBrandMention.entity_name, PostingBrandMention.entity_type)
            .order_by(literal_column("cnt").desc())
            .limit(30)
        )
        unresolved_result = await session.execute(unresolved_stmt)
        unresolved_rows = unresolved_result.all()

        if unresolved_rows:
            print(f"  [INFO] Top unresolved entities ({len(unresolved_rows)} shown):")
            for row in unresolved_rows:
                print(f"    {row.entity_name} ({row.entity_type}): {row.cnt} mentions")
        else:
            print("  [OK] All entity mentions are resolved to brands/retailers")

        # Also show total resolved brand count for context
        brand_count_stmt = select(func.count()).select_from(Brand)
        brand_count = (await session.execute(brand_count_stmt)).scalar() or 0
        mention_count_stmt = select(func.count()).select_from(PostingBrandMention)
        mention_count = (await session.execute(mention_count_stmt)).scalar() or 0
        print(f"\n  [INFO] Total: {brand_count} brands, {mention_count} brand mentions")

        # Also count unresolved via raw SQL for entities that resolved to
        # NEW brands/retailers (is_new=True equivalent — created by resolver)
        new_brands_stmt = text("""
            SELECT b.name, COUNT(pbm.id) AS mention_count
            FROM brands b
            JOIN posting_brand_mentions pbm ON pbm.resolved_brand_id = b.id
            WHERE b.created_at > NOW() - INTERVAL '30 days'
            GROUP BY b.name
            ORDER BY mention_count DESC
            LIMIT 15
        """)
        try:
            new_brands_result = await session.execute(new_brands_stmt)
            new_brands = new_brands_result.all()
            if new_brands:
                print("\n  [INFO] Recently auto-created brands (last 30 days):")
                for row in new_brands:
                    print(f"    {row[0]}: {row[1]} mentions")
        except Exception:
            # brands table may not have created_at — skip gracefully
            logger.debug("Could not query recently created brands", exc_info=True)

    return warnings


async def main_async(args: argparse.Namespace) -> int:
    """Run all checks and print summary."""
    print("CompGraph Data Quality Review — M3 Exit Criterion")
    print(f"{'=' * 70}")

    warnings = await run_checks(verbose=args.verbose)

    print(f"\n{'=' * 70}")
    if warnings > 0:
        print(f"RESULT: {warnings} WARNING(s) found — review items above")
    else:
        print("RESULT: All checks passed — OK")
    print("=" * 70)

    return 1 if warnings > 0 else 0


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
