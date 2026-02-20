"""Tests for enrichment schema Literal type validators (FL12).

Validates that _coerce_literal validators gracefully handle hallucinated
LLM output by coercing invalid values to None (or 'ambiguous' for entity_type).
"""

from __future__ import annotations

import pytest

from compgraph.enrichment.schemas import EntityMention, Pass1Result


class TestPass1LiteralCoercion:
    """Pass1Result validators coerce invalid categorical values to None."""

    def test_valid_role_archetype_preserved(self) -> None:
        result = Pass1Result(role_archetype="field_rep")
        assert result.role_archetype == "field_rep"

    def test_invalid_role_archetype_coerced_to_none(self) -> None:
        result = Pass1Result(role_archetype="hallucinated_role")
        assert result.role_archetype is None

    def test_none_role_archetype_stays_none(self) -> None:
        result = Pass1Result(role_archetype=None)
        assert result.role_archetype is None

    def test_valid_role_level_preserved(self) -> None:
        result = Pass1Result(role_level="entry")
        assert result.role_level == "entry"

    def test_invalid_role_level_coerced_to_none(self) -> None:
        result = Pass1Result(role_level="executive")
        assert result.role_level is None

    def test_valid_employment_type_preserved(self) -> None:
        result = Pass1Result(employment_type="full_time")
        assert result.employment_type == "full_time"

    def test_invalid_employment_type_coerced_to_none(self) -> None:
        result = Pass1Result(employment_type="freelance")
        assert result.employment_type is None

    def test_valid_pay_type_preserved(self) -> None:
        result = Pass1Result(pay_type="hourly")
        assert result.pay_type == "hourly"

    def test_invalid_pay_type_coerced_to_none(self) -> None:
        result = Pass1Result(pay_type="stipend")
        assert result.pay_type is None

    def test_valid_pay_frequency_preserved(self) -> None:
        result = Pass1Result(pay_frequency="hour")
        assert result.pay_frequency == "hour"

    def test_invalid_pay_frequency_coerced_to_none(self) -> None:
        result = Pass1Result(pay_frequency="biweekly")
        assert result.pay_frequency is None

    @pytest.mark.parametrize(
        ("field", "bad_value"),
        [
            ("role_archetype", "FIELD_REP"),
            ("role_level", "Entry"),
            ("employment_type", "Full Time"),
            ("pay_type", "Hourly"),
            ("pay_frequency", "annually"),
        ],
    )
    def test_case_sensitive_coercion(self, field: str, bad_value: str) -> None:
        """Validators are case-sensitive — wrong case is coerced to None."""
        result = Pass1Result(**{field: bad_value})
        assert getattr(result, field) is None


class TestEntityTypeCoercion:
    """EntityMention.entity_type coerces invalid values to 'ambiguous'."""

    def test_valid_entity_type_preserved(self) -> None:
        entity = EntityMention(entity_name="Coca-Cola", entity_type="client_brand", confidence=0.9)
        assert entity.entity_type == "client_brand"

    def test_invalid_entity_type_coerced_to_ambiguous(self) -> None:
        entity = EntityMention(entity_name="Acme", entity_type="unknown_type", confidence=0.8)
        assert entity.entity_type == "ambiguous"

    def test_retailer_entity_type_preserved(self) -> None:
        entity = EntityMention(entity_name="Walmart", entity_type="retailer", confidence=0.95)
        assert entity.entity_type == "retailer"

    def test_ambiguous_entity_type_preserved(self) -> None:
        entity = EntityMention(entity_name="Target", entity_type="ambiguous", confidence=0.5)
        assert entity.entity_type == "ambiguous"
