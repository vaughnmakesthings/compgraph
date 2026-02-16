"""Tests for entity resolver — matching extracted entities against dimension tables."""

from __future__ import annotations

from compgraph.enrichment.resolver import normalize_entity_name
from compgraph.enrichment.schemas import EntityMention

# ---------------------------------------------------------------------------
# normalize_entity_name()
# ---------------------------------------------------------------------------


class TestNormalizeEntityName:
    def test_strips_whitespace(self):
        assert normalize_entity_name("  Samsung  ") == "Samsung"

    def test_removes_possessive(self):
        assert normalize_entity_name("Walmart's") == "Walmart"

    def test_preserves_normal_name(self):
        assert normalize_entity_name("Best Buy") == "Best Buy"

    def test_removes_possessive_with_whitespace(self):
        assert normalize_entity_name(" Target's ") == "Target"

    def test_empty_string(self):
        assert normalize_entity_name("") == ""

    def test_no_possessive_apostrophe_mid_word(self):
        """O'Reilly should NOT have the 's removed — it's not a possessive."""
        # The regex only matches 's at end of string
        assert normalize_entity_name("O'Reilly") == "O'Reilly"


# ---------------------------------------------------------------------------
# Entity resolution (unit tests without DB)
# ---------------------------------------------------------------------------


class TestEntityMentionSchema:
    def test_brand_mention(self):
        mention = EntityMention(
            entity_name="Samsung",
            entity_type="client_brand",
            confidence=0.95,
        )
        assert mention.entity_name == "Samsung"
        assert mention.entity_type == "client_brand"

    def test_retailer_mention(self):
        mention = EntityMention(
            entity_name="Best Buy",
            entity_type="retailer",
            confidence=0.9,
        )
        assert mention.entity_type == "retailer"

    def test_ambiguous_mention(self):
        mention = EntityMention(
            entity_name="Apple",
            entity_type="ambiguous",
            confidence=0.7,
        )
        assert mention.entity_type == "ambiguous"


# ---------------------------------------------------------------------------
# Fuzzy matching thresholds
# ---------------------------------------------------------------------------


class TestFuzzyThresholds:
    def test_thresholds_defined(self):
        from compgraph.enrichment.resolver import (
            AUTO_ACCEPT_THRESHOLD,
            EXACT_THRESHOLD,
            REVIEW_THRESHOLD,
        )

        assert EXACT_THRESHOLD == 100
        assert AUTO_ACCEPT_THRESHOLD == 85
        assert REVIEW_THRESHOLD == 70
        assert AUTO_ACCEPT_THRESHOLD > REVIEW_THRESHOLD

    def test_rapidfuzz_token_sort_ratio(self):
        """Verify rapidfuzz produces expected scores for our use cases."""
        from rapidfuzz import fuzz

        # Exact match
        assert fuzz.token_sort_ratio("Samsung", "Samsung") == 100.0

        # Case match — resolver lowercases both sides before comparing
        score = fuzz.token_sort_ratio("samsung", "samsung")
        assert score == 100.0

        # Partial match — abbreviation
        score = fuzz.token_sort_ratio("best buy", "best buy co")
        assert score > 70  # Should be above review threshold

        # Very different names
        score = fuzz.token_sort_ratio("samsung", "walmart")
        assert score < 70  # Should be below review threshold

    def test_slugify(self):
        """Verify python-slugify produces expected slugs."""
        from slugify import slugify

        assert slugify("Best Buy") == "best-buy"
        assert slugify("Samsung Electronics") == "samsung-electronics"
        assert slugify("Walmart's") == "walmart-s"
        assert slugify("O'Reilly Auto Parts") == "o-reilly-auto-parts"


# ---------------------------------------------------------------------------
# Orchestrator Pass 2 extensions
# ---------------------------------------------------------------------------


class TestEnrichmentRunPass2:
    def test_finish_pass2(self):
        from compgraph.enrichment.orchestrator import (
            EnrichmentRun,
            EnrichmentStatus,
            EnrichResult,
        )

        run = EnrichmentRun()
        result = EnrichResult(succeeded=5, failed=1)
        run.finish_pass2(result)
        assert run.pass2_result is result
        assert run.status == EnrichmentStatus.PARTIAL
        assert run.finished_at is not None

    def test_finish_pass2_success(self):
        from compgraph.enrichment.orchestrator import (
            EnrichmentRun,
            EnrichmentStatus,
            EnrichResult,
        )

        run = EnrichmentRun()
        result = EnrichResult(succeeded=10, failed=0)
        run.finish_pass2(result)
        assert run.status == EnrichmentStatus.SUCCESS

    def test_finish_pass2_empty(self):
        from compgraph.enrichment.orchestrator import (
            EnrichmentRun,
            EnrichmentStatus,
            EnrichResult,
        )

        run = EnrichmentRun()
        result = EnrichResult(succeeded=0, failed=0)
        run.finish_pass2(result)
        assert run.status == EnrichmentStatus.SUCCESS
