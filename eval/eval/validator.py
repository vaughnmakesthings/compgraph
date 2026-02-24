"""Schema compliance validation for LLM evaluation outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from eval.store import EvalStore

VALID_ROLE_ARCHETYPES = {
    "field_rep",
    "merchandiser",
    "brand_ambassador",
    "demo_specialist",
    "team_lead",
    "manager",
    "recruiter",
    "corporate",
    "other",
}
VALID_ROLE_LEVELS = {"entry", "mid", "senior", "lead", "manager", "director"}
VALID_EMPLOYMENT_TYPES = {"full_time", "part_time", "contract", "seasonal", "intern"}
VALID_PAY_TYPES = {"hourly", "salary", "commission"}
VALID_PAY_FREQUENCIES = {"hour", "week", "month", "year"}


@dataclass
class ValidationResult:
    field: str
    value: Any
    valid: bool
    reason: str | None = None


def _check_enum(field_name: str, value: Any, valid_set: set[str]) -> ValidationResult:
    """Check if a value is in an allowed enum set (case-insensitive)."""
    if value is None:
        return ValidationResult(field=field_name, value=value, valid=True)
    if not isinstance(value, str):
        return ValidationResult(
            field=field_name,
            value=value,
            valid=False,
            reason=f"expected string, got {type(value).__name__}",
        )
    if value.lower() not in valid_set:
        return ValidationResult(
            field=field_name,
            value=value,
            valid=False,
            reason=f"unknown {field_name}: {value}",
        )
    return ValidationResult(field=field_name, value=value, valid=True)


def _check_bool(field_name: str, value: Any) -> ValidationResult:
    """Check if a value is actually a boolean (not a string)."""
    if value is None:
        return ValidationResult(field=field_name, value=value, valid=True)
    if not isinstance(value, bool):
        return ValidationResult(
            field=field_name,
            value=value,
            valid=False,
            reason=f"expected bool, got {type(value).__name__}: {value}",
        )
    return ValidationResult(field=field_name, value=value, valid=True)


def _check_pay_range(
    pay_min: Any,
    pay_max: Any,
    pay_frequency: str | None,
) -> list[ValidationResult]:
    """Validate pay_min and pay_max are non-negative with min <= max and reasonable range."""
    results = []
    for name, val in [("pay_min", pay_min), ("pay_max", pay_max)]:
        if val is None:
            results.append(ValidationResult(field=name, value=val, valid=True))
            continue
        if not isinstance(val, (int, float)):
            results.append(
                ValidationResult(
                    field=name,
                    value=val,
                    valid=False,
                    reason=f"expected number, got {type(val).__name__}",
                )
            )
            continue
        if val < 0:
            results.append(
                ValidationResult(
                    field=name,
                    value=val,
                    valid=False,
                    reason="negative pay value",
                )
            )
            continue

        # Reasonable range check based on frequency
        freq = (pay_frequency if isinstance(pay_frequency, str) else "").lower()
        if freq in ("hour", "hourly") and val > 500:
            results.append(
                ValidationResult(
                    field=name,
                    value=val,
                    valid=False,
                    reason=f"${val}/hr exceeds reasonable range",
                )
            )
        elif freq in ("year", "salary") and val > 500_000:
            results.append(
                ValidationResult(
                    field=name,
                    value=val,
                    valid=False,
                    reason=f"${val}/yr exceeds reasonable range",
                )
            )
        else:
            results.append(ValidationResult(field=name, value=val, valid=True))

    if (
        pay_min is not None
        and pay_max is not None
        and isinstance(pay_min, (int, float))
        and isinstance(pay_max, (int, float))
        and pay_min > pay_max
    ):
        results.append(
            ValidationResult(
                field="pay_range",
                value=f"{pay_min}-{pay_max}",
                valid=False,
                reason="pay_min exceeds pay_max",
            )
        )
    return results


def _check_list(field_name: str, value: Any) -> ValidationResult:
    """Check that list fields are actual lists without duplicates."""
    if value is None:
        return ValidationResult(field=field_name, value=value, valid=True)
    if not isinstance(value, list):
        return ValidationResult(
            field=field_name,
            value=value,
            valid=False,
            reason=f"expected list, got {type(value).__name__}",
        )
    if len(value) != len(set(str(v) for v in value)):
        return ValidationResult(
            field=field_name,
            value=value,
            valid=False,
            reason="contains duplicates",
        )
    return ValidationResult(field=field_name, value=value, valid=True)


def _check_non_negative_int(field_name: str, value: Any) -> ValidationResult:
    """Check that a value is a non-negative integer."""
    if value is None:
        return ValidationResult(field=field_name, value=value, valid=True)
    if not isinstance(value, int) or isinstance(value, bool):
        return ValidationResult(
            field=field_name,
            value=value,
            valid=False,
            reason=f"expected integer, got {type(value).__name__}",
        )
    if value < 0:
        return ValidationResult(
            field=field_name,
            value=value,
            valid=False,
            reason="negative value",
        )
    return ValidationResult(field=field_name, value=value, valid=True)


def validate_pass1(parsed: dict) -> list[ValidationResult]:
    """Check all fields of a Pass 1 result against expected enums and ranges."""
    results = []
    results.append(
        _check_enum("role_archetype", parsed.get("role_archetype"), VALID_ROLE_ARCHETYPES)
    )
    results.append(_check_enum("role_level", parsed.get("role_level"), VALID_ROLE_LEVELS))
    results.append(
        _check_enum("employment_type", parsed.get("employment_type"), VALID_EMPLOYMENT_TYPES)
    )
    results.append(_check_enum("pay_type", parsed.get("pay_type"), VALID_PAY_TYPES))
    results.append(_check_enum("pay_frequency", parsed.get("pay_frequency"), VALID_PAY_FREQUENCIES))
    results.extend(
        _check_pay_range(
            parsed.get("pay_min"),
            parsed.get("pay_max"),
            parsed.get("pay_frequency"),
        )
    )
    results.append(_check_bool("has_commission", parsed.get("has_commission")))
    results.append(_check_bool("has_benefits", parsed.get("has_benefits")))
    results.append(_check_bool("travel_required", parsed.get("travel_required")))
    results.append(_check_list("tools_mentioned", parsed.get("tools_mentioned")))
    results.append(_check_list("kpis_mentioned", parsed.get("kpis_mentioned")))
    results.append(_check_non_negative_int("store_count", parsed.get("store_count")))
    return results


@dataclass
class RunValidation:
    run_id: int
    compliance_rate: float = 0.0
    field_compliance: dict[str, float] = field(default_factory=dict)
    common_violations: list[tuple[str, str, int]] = field(default_factory=list)


async def validate_run(store: EvalStore, run_id: int) -> RunValidation:
    """Validate all results in a run for schema compliance."""
    results = await store.get_results(run_id)
    if not results:
        return RunValidation(run_id=run_id)

    field_totals: dict[str, int] = {}
    field_valid: dict[str, int] = {}
    violation_counts: dict[tuple[str, str], int] = {}
    total_checks = 0
    total_valid = 0

    for result in results:
        if not result["parsed_result"]:
            continue
        parsed = (
            json.loads(result["parsed_result"])
            if isinstance(result["parsed_result"], str)
            else result["parsed_result"]
        )
        validations = validate_pass1(parsed)

        for v in validations:
            field_totals[v.field] = field_totals.get(v.field, 0) + 1
            total_checks += 1
            if v.valid:
                field_valid[v.field] = field_valid.get(v.field, 0) + 1
                total_valid += 1
            elif v.reason:
                key = (v.field, str(v.value))
                violation_counts[key] = violation_counts.get(key, 0) + 1

    compliance_rate = total_valid / total_checks if total_checks > 0 else 0.0
    field_compliance = {
        f: field_valid.get(f, 0) / field_totals[f] for f in field_totals if field_totals[f] > 0
    }

    # Sort violations by count descending
    sorted_violations = sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)
    common_violations = [(f, v, c) for (f, v), c in sorted_violations]

    return RunValidation(
        run_id=run_id,
        compliance_rate=compliance_rate,
        field_compliance=field_compliance,
        common_violations=common_violations,
    )
