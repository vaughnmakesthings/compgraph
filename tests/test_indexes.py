from __future__ import annotations

from compgraph.db.models import (
    AggPayBenchmarks,
    AggPostingLifecycle,
    PostingBrandMention,
    PostingEnrichment,
)


class TestPostingEnrichmentIndexes:
    def test_posting_version_composite_index(self) -> None:
        table = PostingEnrichment.__table__
        index_names = {idx.name for idx in table.indexes}
        assert "ix_posting_enrichment_posting_version" in index_names

    def test_brand_id_index(self) -> None:
        table = PostingEnrichment.__table__
        index_names = {idx.name for idx in table.indexes}
        assert "ix_posting_enrichment_brand_id" in index_names

    def test_retailer_id_index(self) -> None:
        table = PostingEnrichment.__table__
        index_names = {idx.name for idx in table.indexes}
        assert "ix_posting_enrichment_retailer_id" in index_names

    def test_market_id_index(self) -> None:
        table = PostingEnrichment.__table__
        index_names = {idx.name for idx in table.indexes}
        assert "ix_posting_enrichment_market_id" in index_names

    def test_posting_version_index_columns(self) -> None:
        table = PostingEnrichment.__table__
        idx = next(i for i in table.indexes if i.name == "ix_posting_enrichment_posting_version")
        col_names = [c.name for c in idx.columns]
        assert col_names == ["posting_id", "enrichment_version"]

    def test_check_constraints_preserved(self) -> None:
        table = PostingEnrichment.__table__
        constraint_names = {c.name for c in table.constraints if hasattr(c, "sqltext")}
        assert "check_pay_min_positive" in constraint_names
        assert "check_pay_max_positive" in constraint_names
        assert "check_pay_range" in constraint_names


class TestPostingBrandMentionIndexes:
    def test_posting_entity_composite_index(self) -> None:
        table = PostingBrandMention.__table__
        index_names = {idx.name for idx in table.indexes}
        assert "ix_posting_brand_mention_posting_entity" in index_names

    def test_posting_entity_index_columns(self) -> None:
        table = PostingBrandMention.__table__
        idx = next(i for i in table.indexes if i.name == "ix_posting_brand_mention_posting_entity")
        col_names = [c.name for c in idx.columns]
        assert col_names == ["posting_id", "entity_type"]


class TestAggPayBenchmarksIndexes:
    def test_company_role_composite_index(self) -> None:
        table = AggPayBenchmarks.__table__
        index_names = {idx.name for idx in table.indexes}
        assert "ix_agg_pay_benchmarks_company_role" in index_names

    def test_company_role_index_columns(self) -> None:
        table = AggPayBenchmarks.__table__
        idx = next(i for i in table.indexes if i.name == "ix_agg_pay_benchmarks_company_role")
        col_names = [c.name for c in idx.columns]
        assert col_names == ["company_id", "role_archetype"]


class TestAggPostingLifecycleIndexes:
    def test_company_period_composite_index(self) -> None:
        table = AggPostingLifecycle.__table__
        index_names = {idx.name for idx in table.indexes}
        assert "ix_agg_posting_lifecycle_company_period" in index_names

    def test_company_period_index_columns(self) -> None:
        table = AggPostingLifecycle.__table__
        idx = next(i for i in table.indexes if i.name == "ix_agg_posting_lifecycle_company_period")
        col_names = [c.name for c in idx.columns]
        assert col_names == ["company_id", "period"]
