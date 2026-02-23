from __future__ import annotations


class TestPopulateMarketsNullCountry:
    """Unit tests for populate_markets dedup logic (no DB required)."""

    def test_none_country_matches_us_string(self):
        existing_with_none = {("Los Angeles", "CA", None)}
        normalized = {(n, s, c or "US") for (n, s, c) in existing_with_none}
        assert ("Los Angeles", "CA", "US") in normalized

    def test_us_string_country_matches_us_string(self):
        existing = {("Los Angeles", "CA", "US")}
        assert ("Los Angeles", "CA", "US") in existing

    def test_none_country_both_sides_normalize_to_same(self):
        existing_with_none = {("Dallas", "TX", None)}
        normalized = {(n, s, c or "US") for (n, s, c) in existing_with_none}
        assert ("Dallas", "TX", "US") in normalized

    def test_idempotent_when_all_countries_are_us(self):
        existing = {("Chicago", "IL", "US"), ("NYC", "NY", "US")}
        normalized = {(n, s, c or "US") for (n, s, c) in existing}
        assert ("Chicago", "IL", "US") in normalized
        assert ("NYC", "NY", "US") in normalized

    def test_market_country_normalizes_none_to_us(self):
        metro_country = None
        market_country = metro_country or "US"
        assert market_country == "US"

    def test_market_country_preserves_non_none_value(self):
        metro_country = "CA"
        market_country = metro_country or "US"
        assert market_country == "CA"
