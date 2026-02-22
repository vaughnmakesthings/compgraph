from __future__ import annotations

import uuid
from datetime import date

from compgraph.db.models import (
    AggBrandAgencyOverlap,
    AggBrandChurnSignals,
    AggMarketCoverageGaps,
    LocationMapping,
    Market,
)


class TestLocationMapping:
    def test_tablename(self):
        assert LocationMapping.__tablename__ == "location_mappings"

    def test_required_columns_exist(self):
        table = LocationMapping.__table__
        expected = [
            "id",
            "city_normalized",
            "state",
            "country",
            "metro_name",
            "metro_state",
            "metro_country",
            "created_at",
        ]
        for col_name in expected:
            assert col_name in table.c, f"Missing column: {col_name}"

    def test_unique_constraint(self):
        table = LocationMapping.__table__
        constraint_names = [c.name for c in table.constraints if c.name]
        assert "uq_location_mapping" in constraint_names

    def test_unique_constraint_columns(self):
        table = LocationMapping.__table__
        uq = next(c for c in table.constraints if c.name == "uq_location_mapping")
        col_names = {col.name for col in uq.columns}
        assert col_names == {"city_normalized", "state", "country"}

    def test_country_defaults(self):
        table = LocationMapping.__table__
        assert table.c["country"].default.arg == "US"
        assert table.c["metro_country"].default.arg == "US"

    def test_instantiation(self):
        mapping = LocationMapping(
            id=uuid.uuid4(),
            city_normalized="san francisco",
            state="CA",
            country="US",
            metro_name="San Francisco-Oakland-San Jose",
            metro_state="CA",
            metro_country="US",
        )
        assert mapping.city_normalized == "san francisco"
        assert mapping.country == "US"
        assert mapping.metro_country == "US"

    def test_city_normalized_not_nullable(self):
        table = LocationMapping.__table__
        assert not table.c["city_normalized"].nullable

    def test_state_string_length(self):
        table = LocationMapping.__table__
        assert table.c["state"].type.length == 10
        assert table.c["metro_state"].type.length == 10


class TestMarketCountry:
    def test_country_column_exists(self):
        table = Market.__table__
        assert "country" in table.c

    def test_country_is_nullable(self):
        table = Market.__table__
        assert table.c["country"].nullable is True

    def test_country_default_is_us(self):
        table = Market.__table__
        assert table.c["country"].default.arg == "US"

    def test_country_max_length(self):
        table = Market.__table__
        assert table.c["country"].type.length == 2

    def test_instantiation_with_country(self):
        market = Market(
            id=uuid.uuid4(),
            name="San Francisco",
            state="CA",
            country="US",
        )
        assert market.country == "US"

    def test_column_default_applies_on_flush(self):
        table = Market.__table__
        col = table.c["country"]
        assert col.default is not None
        assert col.default.arg == "US"
        assert col.nullable is True


class TestAggBrandChurnSignals:
    def test_tablename(self):
        assert AggBrandChurnSignals.__tablename__ == "agg_brand_churn_signals"

    def test_required_columns_exist(self):
        table = AggBrandChurnSignals.__table__
        expected = [
            "id",
            "company_id",
            "brand_id",
            "period",
            "active_posting_count",
            "prior_period_count",
            "velocity_delta",
            "avg_days_active",
            "repost_rate",
            "churn_signal_score",
        ]
        for col_name in expected:
            assert col_name in table.c, f"Missing column: {col_name}"

    def test_index_on_company_brand(self):
        table = AggBrandChurnSignals.__table__
        index_names = [idx.name for idx in table.indexes]
        assert "ix_churn_signals_company_brand" in index_names

    def test_index_columns(self):
        table = AggBrandChurnSignals.__table__
        idx = next(i for i in table.indexes if i.name == "ix_churn_signals_company_brand")
        col_names = [col.name for col in idx.columns]
        assert col_names == ["company_id", "brand_id"]

    def test_uuid_primary_key(self):
        table = AggBrandChurnSignals.__table__
        assert table.c["id"].primary_key

    def test_foreign_keys(self):
        table = AggBrandChurnSignals.__table__
        company_fks = [fk.target_fullname for fk in table.c["company_id"].foreign_keys]
        brand_fks = [fk.target_fullname for fk in table.c["brand_id"].foreign_keys]
        assert "companies.id" in company_fks
        assert "brands.id" in brand_fks

    def test_instantiation(self):
        row = AggBrandChurnSignals(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            brand_id=uuid.uuid4(),
            period=date(2026, 2, 1),
            active_posting_count=10,
            prior_period_count=15,
            velocity_delta=-5.0,
            avg_days_active=14.5,
            repost_rate=0.2,
            churn_signal_score=0.75,
        )
        assert row.active_posting_count == 10
        assert row.velocity_delta == -5.0


class TestAggMarketCoverageGaps:
    def test_tablename(self):
        assert AggMarketCoverageGaps.__tablename__ == "agg_market_coverage_gaps"

    def test_required_columns_exist(self):
        table = AggMarketCoverageGaps.__table__
        expected = [
            "id",
            "company_id",
            "market_id",
            "period",
            "total_active_postings",
            "brand_count",
            "brand_names",
        ]
        for col_name in expected:
            assert col_name in table.c, f"Missing column: {col_name}"

    def test_index_on_company_market(self):
        table = AggMarketCoverageGaps.__table__
        index_names = [idx.name for idx in table.indexes]
        assert "ix_coverage_gaps_company_market" in index_names

    def test_index_columns(self):
        table = AggMarketCoverageGaps.__table__
        idx = next(i for i in table.indexes if i.name == "ix_coverage_gaps_company_market")
        col_names = [col.name for col in idx.columns]
        assert col_names == ["company_id", "market_id"]

    def test_brand_names_is_array(self):
        table = AggMarketCoverageGaps.__table__
        col = table.c["brand_names"]
        assert col.nullable is True
        assert hasattr(col.type, "item_type")

    def test_foreign_keys(self):
        table = AggMarketCoverageGaps.__table__
        company_fks = [fk.target_fullname for fk in table.c["company_id"].foreign_keys]
        market_fks = [fk.target_fullname for fk in table.c["market_id"].foreign_keys]
        assert "companies.id" in company_fks
        assert "markets.id" in market_fks

    def test_instantiation(self):
        row = AggMarketCoverageGaps(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            market_id=uuid.uuid4(),
            period=date(2026, 2, 1),
            total_active_postings=25,
            brand_count=3,
            brand_names=["Samsung", "LG", "Sony"],
        )
        assert row.brand_count == 3
        assert row.brand_names == ["Samsung", "LG", "Sony"]


class TestAggBrandAgencyOverlap:
    def test_tablename(self):
        assert AggBrandAgencyOverlap.__tablename__ == "agg_brand_agency_overlap"

    def test_required_columns_exist(self):
        table = AggBrandAgencyOverlap.__table__
        expected = [
            "id",
            "brand_id",
            "period",
            "agency_count",
            "agency_names",
            "primary_company_id",
            "primary_share",
            "is_exclusive",
            "is_contested",
            "total_postings",
        ]
        for col_name in expected:
            assert col_name in table.c, f"Missing column: {col_name}"

    def test_index_on_brand(self):
        table = AggBrandAgencyOverlap.__table__
        index_names = [idx.name for idx in table.indexes]
        assert "ix_agency_overlap_brand" in index_names

    def test_index_columns(self):
        table = AggBrandAgencyOverlap.__table__
        idx = next(i for i in table.indexes if i.name == "ix_agency_overlap_brand")
        col_names = [col.name for col in idx.columns]
        assert col_names == ["brand_id"]

    def test_agency_names_is_array(self):
        table = AggBrandAgencyOverlap.__table__
        col = table.c["agency_names"]
        assert col.nullable is True
        assert hasattr(col.type, "item_type")

    def test_primary_company_id_nullable(self):
        table = AggBrandAgencyOverlap.__table__
        assert table.c["primary_company_id"].nullable is True

    def test_foreign_keys(self):
        table = AggBrandAgencyOverlap.__table__
        brand_fks = [fk.target_fullname for fk in table.c["brand_id"].foreign_keys]
        primary_fks = [fk.target_fullname for fk in table.c["primary_company_id"].foreign_keys]
        assert "brands.id" in brand_fks
        assert "companies.id" in primary_fks

    def test_boolean_defaults(self):
        table = AggBrandAgencyOverlap.__table__
        assert table.c["is_exclusive"].default.arg is False
        assert table.c["is_contested"].default.arg is False

    def test_instantiation(self):
        row = AggBrandAgencyOverlap(
            id=uuid.uuid4(),
            brand_id=uuid.uuid4(),
            period=date(2026, 2, 1),
            agency_count=3,
            agency_names=["BDS", "MarketSource", "2020 Companies"],
            primary_company_id=uuid.uuid4(),
            primary_share=0.55,
            is_exclusive=False,
            is_contested=True,
            total_postings=42,
        )
        assert row.agency_count == 3
        assert row.is_contested is True
        assert row.is_exclusive is False
        assert row.primary_share == 0.55
