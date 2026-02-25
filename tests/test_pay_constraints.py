from __future__ import annotations

import pytest
from pydantic import ValidationError

from compgraph.enrichment.schemas import PAY_RANGE_BY_FREQUENCY, Pass1Result


class TestHourlyPayRange:
    def test_valid_hourly_min(self) -> None:
        result = Pass1Result(pay_min=25.0, pay_frequency="hour")
        assert result.pay_min == 25.0

    def test_valid_hourly_max(self) -> None:
        result = Pass1Result(pay_max=50.0, pay_frequency="hour")
        assert result.pay_max == 50.0

    def test_valid_hourly_range(self) -> None:
        result = Pass1Result(pay_min=15.0, pay_max=30.0, pay_frequency="hour")
        assert result.pay_min == 15.0
        assert result.pay_max == 30.0

    def test_hourly_at_lower_bound(self) -> None:
        result = Pass1Result(pay_min=10.0, pay_frequency="hour")
        assert result.pay_min == 10.0

    def test_hourly_at_upper_bound(self) -> None:
        result = Pass1Result(pay_max=150.0, pay_frequency="hour")
        assert result.pay_max == 150.0

    def test_hourly_below_floor_rejected(self) -> None:
        with pytest.raises(ValidationError, match=r"pay_min .* outside allowed range"):
            Pass1Result(pay_min=5.0, pay_frequency="hour")

    def test_hourly_above_ceiling_rejected(self) -> None:
        with pytest.raises(ValidationError, match=r"pay_max .* outside allowed range"):
            Pass1Result(pay_max=200.0, pay_frequency="hour")

    def test_hourly_min_above_ceiling_rejected(self) -> None:
        with pytest.raises(ValidationError, match=r"pay_min .* outside allowed range"):
            Pass1Result(pay_min=500.0, pay_frequency="hour")


class TestAnnualPayRange:
    def test_valid_annual_salary(self) -> None:
        result = Pass1Result(pay_min=50_000.0, pay_max=80_000.0, pay_frequency="year")
        assert result.pay_min == 50_000.0
        assert result.pay_max == 80_000.0

    def test_annual_at_lower_bound(self) -> None:
        result = Pass1Result(pay_min=20_000.0, pay_frequency="year")
        assert result.pay_min == 20_000.0

    def test_annual_at_upper_bound(self) -> None:
        result = Pass1Result(pay_max=300_000.0, pay_frequency="year")
        assert result.pay_max == 300_000.0

    def test_annual_below_floor_rejected(self) -> None:
        with pytest.raises(ValidationError, match=r"pay_min .* outside allowed range"):
            Pass1Result(pay_min=10_000.0, pay_frequency="year")

    def test_annual_above_ceiling_rejected(self) -> None:
        with pytest.raises(ValidationError, match=r"pay_max .* outside allowed range"):
            Pass1Result(pay_max=500_000.0, pay_frequency="year")

    def test_million_dollar_budget_rejected(self) -> None:
        with pytest.raises(ValidationError, match="outside allowed range"):
            Pass1Result(pay_max=1_000_000.0, pay_frequency="year")

    def test_annual_min_below_floor_rejected(self) -> None:
        with pytest.raises(ValidationError, match=r"pay_min .* outside allowed range"):
            Pass1Result(pay_min=5_000.0, pay_frequency="year")


class TestWeeklyPayRange:
    def test_valid_weekly_pay(self) -> None:
        result = Pass1Result(pay_min=800.0, pay_max=2_000.0, pay_frequency="week")
        assert result.pay_min == 800.0
        assert result.pay_max == 2_000.0

    def test_weekly_below_floor_rejected(self) -> None:
        with pytest.raises(ValidationError, match="outside allowed range"):
            Pass1Result(pay_min=100.0, pay_frequency="week")

    def test_weekly_above_ceiling_rejected(self) -> None:
        with pytest.raises(ValidationError, match="outside allowed range"):
            Pass1Result(pay_max=10_000.0, pay_frequency="week")


class TestMonthlyPayRange:
    def test_valid_monthly_pay(self) -> None:
        result = Pass1Result(pay_min=3_000.0, pay_max=8_000.0, pay_frequency="month")
        assert result.pay_min == 3_000.0
        assert result.pay_max == 8_000.0

    def test_monthly_below_floor_rejected(self) -> None:
        with pytest.raises(ValidationError, match="outside allowed range"):
            Pass1Result(pay_min=500.0, pay_frequency="month")

    def test_monthly_above_ceiling_rejected(self) -> None:
        with pytest.raises(ValidationError, match="outside allowed range"):
            Pass1Result(pay_max=50_000.0, pay_frequency="month")


class TestCrossFieldValidation:
    def test_min_exceeds_max_rejected(self) -> None:
        with pytest.raises(ValidationError, match=r"pay_min .* must not exceed pay_max"):
            Pass1Result(pay_min=30.0, pay_max=20.0, pay_frequency="hour")

    def test_min_equals_max_accepted(self) -> None:
        result = Pass1Result(pay_min=25.0, pay_max=25.0, pay_frequency="hour")
        assert result.pay_min == result.pay_max == 25.0

    def test_annual_min_exceeds_max_rejected(self) -> None:
        with pytest.raises(ValidationError, match=r"pay_min .* must not exceed pay_max"):
            Pass1Result(pay_min=80_000.0, pay_max=50_000.0, pay_frequency="year")


class TestNullPayValues:
    def test_all_pay_fields_none(self) -> None:
        result = Pass1Result()
        assert result.pay_min is None
        assert result.pay_max is None
        assert result.pay_frequency is None

    def test_only_frequency_set(self) -> None:
        result = Pass1Result(pay_frequency="hour")
        assert result.pay_min is None
        assert result.pay_max is None

    def test_min_none_max_present(self) -> None:
        result = Pass1Result(pay_max=25.0, pay_frequency="hour")
        assert result.pay_min is None
        assert result.pay_max == 25.0

    def test_min_present_max_none(self) -> None:
        result = Pass1Result(pay_min=15.0, pay_frequency="hour")
        assert result.pay_min == 15.0
        assert result.pay_max is None


class TestNoFrequencyFallback:
    def test_pay_without_frequency_valid_hourly_amount(self) -> None:
        result = Pass1Result(pay_min=25.0, pay_max=50.0)
        assert result.pay_min == 25.0
        assert result.pay_max == 50.0

    def test_pay_without_frequency_valid_annual_amount(self) -> None:
        result = Pass1Result(pay_min=50_000.0, pay_max=80_000.0)
        assert result.pay_min == 50_000.0
        assert result.pay_max == 80_000.0

    def test_pay_without_frequency_rejects_million(self) -> None:
        with pytest.raises(ValidationError, match="outside allowed range"):
            Pass1Result(pay_max=1_000_000.0)

    def test_pay_without_frequency_rejects_below_floor(self) -> None:
        with pytest.raises(ValidationError, match="outside allowed range"):
            Pass1Result(pay_min=5.0)


class TestPayRangeConstants:
    def test_hourly_bounds(self) -> None:
        assert PAY_RANGE_BY_FREQUENCY["hour"] == (10.0, 150.0)

    def test_annual_bounds(self) -> None:
        assert PAY_RANGE_BY_FREQUENCY["year"] == (20_000.0, 300_000.0)

    def test_weekly_bounds(self) -> None:
        assert PAY_RANGE_BY_FREQUENCY["week"] == (400.0, 6_000.0)

    def test_monthly_bounds(self) -> None:
        assert PAY_RANGE_BY_FREQUENCY["month"] == (1_667.0, 25_000.0)

    def test_none_frequency_bounds(self) -> None:
        assert PAY_RANGE_BY_FREQUENCY[None] == (10.0, 300_000.0)


class TestRealWorldLLMErrors:
    def test_contract_total_as_annual_pay_rejected(self) -> None:
        with pytest.raises(ValidationError, match="outside allowed range"):
            Pass1Result(pay_max=500_000.0, pay_frequency="year")

    def test_budget_figure_as_hourly_rejected(self) -> None:
        with pytest.raises(ValidationError, match="outside allowed range"):
            Pass1Result(pay_min=1_000.0, pay_frequency="hour")

    def test_negative_pay_rejected(self) -> None:
        with pytest.raises(ValidationError, match="outside allowed range"):
            Pass1Result(pay_min=-15.0, pay_frequency="hour")

    def test_zero_pay_rejected(self) -> None:
        with pytest.raises(ValidationError, match="outside allowed range"):
            Pass1Result(pay_min=0.0, pay_frequency="hour")

    def test_penny_pay_rejected(self) -> None:
        with pytest.raises(ValidationError, match="outside allowed range"):
            Pass1Result(pay_min=0.50, pay_frequency="hour")
