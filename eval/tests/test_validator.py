"""Tests for schema compliance validator."""

from pathlib import Path

import pytest_asyncio
from eval.store import EvalStore
from eval.validator import (
    RunValidation,
    validate_pass1,
    validate_run,
)

# --- Unit tests for validate_pass1 ---


def test_valid_enums_pass():
    """All valid enum values should pass validation."""
    parsed = {
        "role_archetype": "field_rep",
        "role_level": "entry",
        "employment_type": "full_time",
        "pay_type": "hourly",
        "pay_frequency": "hour",
        "pay_min": 15.0,
        "pay_max": 25.0,
        "has_commission": False,
        "has_benefits": True,
        "travel_required": False,
        "tools_mentioned": ["Repsly"],
        "kpis_mentioned": ["sales"],
        "store_count": 5,
    }
    results = validate_pass1(parsed)
    invalid = [r for r in results if not r.valid]
    assert invalid == [], f"Unexpected failures: {[(r.field, r.reason) for r in invalid]}"


def test_invalid_enum_values_fail():
    """Unknown enum values should fail with reason."""
    parsed = {
        "role_archetype": "sales_associate",
        "role_level": "junior",
        "employment_type": "freelance",
        "pay_type": "stipend",
        "pay_frequency": "annual",
    }
    results = validate_pass1(parsed)
    invalid = {r.field: r.reason for r in results if not r.valid}
    assert "role_archetype" in invalid
    assert "sales_associate" in invalid["role_archetype"]
    assert "role_level" in invalid
    assert "employment_type" in invalid
    assert "pay_type" in invalid
    assert "pay_frequency" in invalid


def test_case_insensitive_enum():
    """Enum validation should be case-insensitive."""
    parsed = {"role_archetype": "Field_Rep", "role_level": "Entry"}
    results = validate_pass1(parsed)
    archetype_result = next(r for r in results if r.field == "role_archetype")
    level_result = next(r for r in results if r.field == "role_level")
    assert archetype_result.valid
    assert level_result.valid


def test_pay_range_validation():
    """Pay range checks: min <= max, non-negative, reasonable bounds."""
    # min > max
    parsed = {"pay_min": 30.0, "pay_max": 20.0, "pay_frequency": "hour"}
    results = validate_pass1(parsed)
    range_check = next((r for r in results if r.field == "pay_range"), None)
    assert range_check is not None
    assert not range_check.valid
    assert "exceeds" in range_check.reason

    # Negative pay
    parsed = {"pay_min": -5.0, "pay_max": 20.0, "pay_frequency": "hour"}
    results = validate_pass1(parsed)
    min_check = next(r for r in results if r.field == "pay_min")
    assert not min_check.valid
    assert "negative" in min_check.reason

    # Unreasonable hourly rate
    parsed = {"pay_min": 15.0, "pay_max": 999.0, "pay_frequency": "hour"}
    results = validate_pass1(parsed)
    max_check = next(r for r in results if r.field == "pay_max")
    assert not max_check.valid
    assert "exceeds" in max_check.reason


def test_boolean_field_validation():
    """Boolean fields reject string 'true' and integers."""
    parsed = {"has_commission": "true", "has_benefits": 1, "travel_required": True}
    results = validate_pass1(parsed)
    comm = next(r for r in results if r.field == "has_commission")
    benefits = next(r for r in results if r.field == "has_benefits")
    travel = next(r for r in results if r.field == "travel_required")
    assert not comm.valid
    assert not benefits.valid
    assert travel.valid


def test_null_fields_pass():
    """All-null parsed result should pass (nulls are acceptable)."""
    parsed = {}
    results = validate_pass1(parsed)
    invalid = [r for r in results if not r.valid]
    assert invalid == []


def test_list_duplicates_fail():
    """List fields with duplicates should fail."""
    parsed = {"tools_mentioned": ["Repsly", "Repsly"]}
    results = validate_pass1(parsed)
    tools = next(r for r in results if r.field == "tools_mentioned")
    assert not tools.valid
    assert "duplicates" in tools.reason


# --- Integration test for validate_run ---


@pytest_asyncio.fixture
async def store_with_run(tmp_path: Path):
    """Create a store with a run containing both valid and invalid results."""
    s = EvalStore(str(tmp_path / "test.db"))
    await s.init()
    await s.insert_corpus(
        [
            {
                "id": "p1",
                "company_slug": "bds",
                "title": "Rep",
                "location": "NY",
                "full_text": "Text",
            },
            {
                "id": "p2",
                "company_slug": "bds",
                "title": "Rep2",
                "location": "CA",
                "full_text": "Text2",
            },
        ]
    )
    run_id = await s.create_run(1, "haiku-4.5", "pass1_v1", 2)

    # Valid result
    await s.insert_result(
        run_id,
        "p1",
        "{}",
        {
            "role_archetype": "field_rep",
            "role_level": "entry",
            "pay_min": 15.0,
            "pay_max": 25.0,
            "pay_frequency": "hour",
            "has_commission": False,
        },
        True,
        100,
        50,
        0.001,
        500,
    )
    # Invalid result (bad enum + min > max)
    await s.insert_result(
        run_id,
        "p2",
        "{}",
        {
            "role_archetype": "sales_associate",
            "pay_min": 30.0,
            "pay_max": 20.0,
            "pay_frequency": "hour",
        },
        True,
        100,
        50,
        0.001,
        500,
    )
    yield s, run_id
    await s.close()


async def test_validate_run_aggregation(store_with_run):
    """validate_run should compute compliance rate and list violations."""
    store, run_id = store_with_run
    validation = await validate_run(store, run_id)

    assert isinstance(validation, RunValidation)
    assert validation.run_id == run_id
    # Should be less than 100% due to invalid result
    assert 0 < validation.compliance_rate < 1.0
    # Should have violations
    assert len(validation.common_violations) > 0
    # Check role_archetype violation is listed
    violation_fields = [f for f, v, c in validation.common_violations]
    assert "role_archetype" in violation_fields
