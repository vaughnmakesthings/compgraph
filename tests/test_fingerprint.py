"""Tests for fingerprinting and repost detection."""

from __future__ import annotations

from compgraph.enrichment.fingerprint import (
    generate_fingerprint,
    normalize_location,
    normalize_title,
)

# ---------------------------------------------------------------------------
# normalize_title()
# ---------------------------------------------------------------------------


class TestNormalizeTitle:
    def test_lowercase(self):
        assert normalize_title("FIELD REP") == "field rep"

    def test_strip_whitespace(self):
        assert normalize_title("  Samsung Rep  ") == "samsung rep"

    def test_strip_field_rep_prefix(self):
        assert normalize_title("Field Rep - Samsung") == "samsung"

    def test_strip_field_representative_prefix(self):
        assert normalize_title("Field Representative: Samsung Galaxy") == "samsung galaxy"

    def test_strip_brand_ambassador_prefix(self):
        assert normalize_title("Brand Ambassador - LG Electronics") == "lg electronics"

    def test_strip_merchandiser_prefix(self):
        assert normalize_title("Merchandiser - Target Stores") == "target stores"

    def test_strip_demo_specialist_prefix(self):
        assert normalize_title("Demo Specialist: Samsung") == "samsung"

    def test_no_prefix_to_strip(self):
        assert normalize_title("Territory Manager") == "territory manager"

    def test_collapse_spaces(self):
        assert normalize_title("Field  Rep  -  Samsung") == "samsung"

    def test_empty_string(self):
        assert normalize_title("") == ""


# ---------------------------------------------------------------------------
# normalize_location()
# ---------------------------------------------------------------------------


class TestNormalizeLocation:
    def test_lowercase(self):
        assert normalize_location("Chicago, IL") == "chicago, il"

    def test_strip_whitespace(self):
        assert normalize_location("  Dallas, TX  ") == "dallas, tx"

    def test_collapse_spaces(self):
        assert normalize_location("New   York,   NY") == "new york, ny"

    def test_empty_string(self):
        assert normalize_location("") == ""


# ---------------------------------------------------------------------------
# generate_fingerprint()
# ---------------------------------------------------------------------------


class TestGenerateFingerprint:
    def test_deterministic(self):
        """Same inputs always produce the same hash."""
        fp1 = generate_fingerprint("Samsung Rep", "Chicago, IL", "samsung")
        fp2 = generate_fingerprint("Samsung Rep", "Chicago, IL", "samsung")
        assert fp1 == fp2

    def test_different_titles_different_hash(self):
        fp1 = generate_fingerprint("Samsung Rep", "Chicago, IL", "samsung")
        fp2 = generate_fingerprint("LG Rep", "Chicago, IL", "samsung")
        assert fp1 != fp2

    def test_different_locations_different_hash(self):
        fp1 = generate_fingerprint("Samsung Rep", "Chicago, IL", "samsung")
        fp2 = generate_fingerprint("Samsung Rep", "Dallas, TX", "samsung")
        assert fp1 != fp2

    def test_different_brands_different_hash(self):
        fp1 = generate_fingerprint("Samsung Rep", "Chicago, IL", "samsung")
        fp2 = generate_fingerprint("Samsung Rep", "Chicago, IL", "lg")
        assert fp1 != fp2

    def test_none_brand_slug(self):
        """None brand_slug should produce a valid hash."""
        fp = generate_fingerprint("Samsung Rep", "Chicago, IL", None)
        assert len(fp) == 64  # SHA-256 hex digest length

    def test_hash_length(self):
        fp = generate_fingerprint("Title", "Location", "brand")
        assert len(fp) == 64

    def test_case_insensitive(self):
        """Normalization makes fingerprints case-insensitive."""
        fp1 = generate_fingerprint("SAMSUNG REP", "CHICAGO, IL", "samsung")
        fp2 = generate_fingerprint("samsung rep", "chicago, il", "samsung")
        assert fp1 == fp2

    def test_prefix_stripping_produces_same_hash(self):
        """'Field Rep - Samsung' and 'Samsung' should produce the same hash."""
        fp1 = generate_fingerprint("Field Rep - Samsung", "Chicago, IL", "samsung")
        fp2 = generate_fingerprint("Samsung", "Chicago, IL", "samsung")
        assert fp1 == fp2

    def test_whitespace_normalization(self):
        fp1 = generate_fingerprint("  Samsung   Rep  ", "  Chicago,   IL  ", "samsung")
        fp2 = generate_fingerprint("Samsung Rep", "Chicago, IL", "samsung")
        assert fp1 == fp2

    def test_empty_inputs(self):
        """Should handle empty strings gracefully."""
        fp = generate_fingerprint("", "", None)
        assert len(fp) == 64

    def test_no_false_positives_similar_titles(self):
        """Similar but different titles should not match."""
        fp1 = generate_fingerprint("Samsung Galaxy Rep", "Chicago, IL", "samsung")
        fp2 = generate_fingerprint("Samsung TV Rep", "Chicago, IL", "samsung")
        assert fp1 != fp2

    def test_delimiter_prevents_collision(self):
        """Titles/locations with pipe characters shouldn't collide.

        With the old `|` delimiter, "a|b" + "c" could collide with "a" + "b|c".
        With `\\0` delimiter this is impossible since NUL can't appear in text.
        """
        fp1 = generate_fingerprint("Field Rep|Best Buy", "Chicago, IL", "samsung")
        fp2 = generate_fingerprint("Field Rep", "Best Buy|Chicago, IL", "samsung")
        assert fp1 != fp2

    def test_none_brand_differs_from_branded(self):
        """None brand should produce a different hash from a real brand."""
        fp_none = generate_fingerprint("Samsung Rep", "Chicago, IL", None)
        fp_brand = generate_fingerprint("Samsung Rep", "Chicago, IL", "samsung")
        assert fp_none != fp_brand
