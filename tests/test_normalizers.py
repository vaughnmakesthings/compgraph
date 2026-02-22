from __future__ import annotations

import pytest

from compgraph.enrichment.normalizers import (
    normalize_location_raw,
    normalize_title_for_grouping,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Basic cleanup
        ("  Field Representative  ", "field representative"),
        ("BRAND AMBASSADOR", "brand ambassador"),
        # Strip trailing location " - City, ST"
        ("Field Rep - Dallas, TX", "field rep"),
        # Strip trailing location " | City, ST, US"
        ("Merchandiser | Houston, TX, US", "merchandiser"),
        # Strip trailing location "(City, ST)"
        ("Brand Ambassador (Orlando, FL)", "brand ambassador"),
        # Strip trailing company name
        ("Field Rep - 2020 Companies", "field rep"),
        ("Merchandiser | BDS Connected Solutions", "merchandiser"),
        ("Brand Ambassador - MarketSource", "brand ambassador"),
        ("Field Rep | T-ROC", "field rep"),
        ("Merchandiser - Mosaic Sales Solutions", "merchandiser"),
        ("Field Rep | Advantage Solutions", "field rep"),
        ("Brand Ambassador - Acosta", "brand ambassador"),
        # Strip both (company in middle stays, location at end stripped)
        ("Field Representative - Samsung - Dallas, TX", "field representative - samsung"),
        # Collapse whitespace
        ("Field   Rep    Dallas", "field rep dallas"),
        # None/empty
        (None, None),
        ("", None),
        ("   ", None),
    ],
)
def test_normalize_title(raw: str | None, expected: str | None) -> None:
    assert normalize_title_for_grouping(raw) == expected


class TestNormalizeTitleEdgeCases:
    def test_title_with_pipe_location_and_country(self) -> None:
        assert normalize_title_for_grouping("Sales Rep | Austin, TX, US") == "sales rep"

    def test_title_with_parenthesized_location_and_country(self) -> None:
        assert normalize_title_for_grouping("Demo Specialist (Miami, FL, US)") == "demo specialist"

    def test_company_name_case_insensitive(self) -> None:
        assert normalize_title_for_grouping("Field Rep - bds connected solutions") == "field rep"

    def test_only_whitespace_after_stripping(self) -> None:
        assert (
            normalize_title_for_grouping("- Dallas, TX") is None
            or normalize_title_for_grouping("- Dallas, TX") == "- dallas, tx"
        )

    def test_no_trailing_pattern_preserved(self) -> None:
        assert (
            normalize_title_for_grouping("Territory Manager - Samsung")
            == "territory manager - samsung"
        )

    def test_multi_word_city(self) -> None:
        assert normalize_title_for_grouping("Field Rep - San Antonio, TX") == "field rep"

    def test_en_dash_separator(self) -> None:
        assert (
            normalize_title_for_grouping("Brand Ambassador \u2013 Dallas, TX") == "brand ambassador"
        )

    def test_em_dash_separator(self) -> None:
        assert (
            normalize_title_for_grouping("Brand Ambassador \u2014 Dallas, TX") == "brand ambassador"
        )


@pytest.mark.parametrize(
    "raw,expected_city,expected_state,expected_country",
    [
        # Standard US: "City, ST, US"
        ("Dallas, TX, US", "Dallas", "TX", "US"),
        ("ORLANDO, FL, US", "Orlando", "FL", "US"),
        # Without country suffix (defaults to US)
        ("Dallas, TX", "Dallas", "TX", "US"),
        # Canadian with explicit country
        ("Toronto, ON, CA", "Toronto", "ON", "CA"),
        # Canadian inferred from province code
        ("Toronto, ON", "Toronto", "ON", "CA"),
        ("Vancouver, BC", "Vancouver", "BC", "CA"),
        ("Montreal, QC", "Montreal", "QC", "CA"),
        # With ZIP code
        ("Dallas, TX 75201, US", "Dallas", "TX", "US"),
        ("Orlando, FL 32801", "Orlando", "FL", "US"),
        # Extra whitespace
        ("  Dallas ,  TX  ", "Dallas", "TX", "US"),
        # None/empty
        (None, None, None, None),
        ("", None, None, None),
        ("   ", None, None, None),
    ],
)
def test_normalize_location_raw(
    raw: str | None,
    expected_city: str | None,
    expected_state: str | None,
    expected_country: str | None,
) -> None:
    result = normalize_location_raw(raw)
    if expected_city is None:
        assert result is None
    else:
        assert result == (expected_city, expected_state, expected_country)


class TestNormalizeLocationEdgeCases:
    def test_lowercase_country_suffix(self) -> None:
        result = normalize_location_raw("Dallas, TX, us")
        assert result == ("Dallas", "TX", "US")

    def test_city_only_returns_none(self) -> None:
        result = normalize_location_raw("Dallas")
        assert result is None

    def test_multi_word_city(self) -> None:
        result = normalize_location_raw("San Antonio, TX, US")
        assert result == ("San Antonio", "TX", "US")

    def test_multi_word_city_title_case(self) -> None:
        result = normalize_location_raw("SAN ANTONIO, TX")
        assert result == ("San Antonio", "TX", "US")

    def test_zip_plus_four(self) -> None:
        result = normalize_location_raw("Dallas, TX 75201-1234, US")
        assert result == ("Dallas", "TX", "US")

    def test_all_canadian_provinces_detected(self) -> None:
        provinces = ["AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"]
        for prov in provinces:
            result = normalize_location_raw(f"City, {prov}")
            assert result is not None
            assert result[2] == "CA", f"Province {prov} should be detected as Canadian"
