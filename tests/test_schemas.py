"""Tests for evaluation schemas and config."""

import pytest
from eval.config import MODELS
from eval.schemas import EntityMention, Pass1Result, Pass2Result


class TestPass1Result:
    def test_all_fields_optional(self):
        """Pass1Result should accept empty input (all fields null/default)."""
        result = Pass1Result()
        assert result.role_archetype is None
        assert result.pay_min is None
        assert result.tools_mentioned == []

    def test_full_result_parses(self):
        """Pass1Result should parse a complete JSON output."""
        data = {
            "role_archetype": "field_rep",
            "role_level": "entry",
            "employment_type": "full_time",
            "travel_required": True,
            "pay_type": "hourly",
            "pay_min": 18.0,
            "pay_max": 22.0,
            "pay_frequency": "hour",
            "has_commission": True,
            "has_benefits": True,
            "content_role_specific": "Visit 15 Best Buy stores weekly.",
            "content_boilerplate": "EEO statement.",
            "content_qualifications": "Must have valid driver's license.",
            "content_responsibilities": "Stock shelves, build displays.",
            "tools_mentioned": ["Salesforce", "Repsly"],
            "kpis_mentioned": ["store visits per day"],
            "store_count": 15,
        }
        result = Pass1Result(**data)
        assert result.role_archetype == "field_rep"
        assert result.pay_min == 18.0
        assert result.tools_mentioned == ["Salesforce", "Repsly"]
        assert result.store_count == 15

    def test_json_roundtrip(self):
        """Pass1Result should survive JSON serialization."""
        data = {"role_archetype": "merchandiser", "pay_min": 15.0, "tools_mentioned": ["Excel"]}
        result = Pass1Result(**data)
        json_str = result.model_dump_json()
        restored = Pass1Result.model_validate_json(json_str)
        assert restored.role_archetype == "merchandiser"
        assert restored.pay_min == 15.0


class TestPass2Result:
    def test_empty_entities(self):
        """Pass2Result should accept empty entities list."""
        result = Pass2Result()
        assert result.entities == []

    def test_entities_parse(self):
        """Pass2Result should parse entity mentions with confidence."""
        data = {
            "entities": [
                {"entity_name": "Samsung", "entity_type": "client_brand", "confidence": 0.95},
                {"entity_name": "Best Buy", "entity_type": "retailer", "confidence": 0.9},
            ]
        }
        result = Pass2Result(**data)
        assert len(result.entities) == 2
        assert result.entities[0].entity_name == "Samsung"
        assert result.entities[1].confidence == 0.9

    def test_confidence_bounds(self):
        """EntityMention should reject confidence outside 0-1."""
        with pytest.raises(Exception):
            EntityMention(entity_name="X", entity_type="client_brand", confidence=1.5)


class TestConfig:
    def test_models_dict_not_empty(self):
        """MODELS config should contain at least one model."""
        assert len(MODELS) > 0

    def test_models_have_string_values(self):
        """Each model alias should map to a LiteLLM model string."""
        for alias, model_id in MODELS.items():
            assert isinstance(alias, str)
            assert isinstance(model_id, str)
            assert len(model_id) > 0
