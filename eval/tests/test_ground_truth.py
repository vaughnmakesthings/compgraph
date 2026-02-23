"""Tests for ground truth extraction, scoring, and diff reporting."""

from __future__ import annotations

from pathlib import Path

import pytest_asyncio
from eval.ground_truth import (
    FieldScore,
    _coerce_type,
    _compare_values,
    compute_diff_report,
    extract_ground_truth,
    score_candidate_run,
    wilson_score_interval,
)
from eval.store import EvalStore


@pytest_asyncio.fixture
async def store(tmp_path: Path):
    """Create a temporary store with corpus for testing."""
    s = EvalStore(str(tmp_path / "test.db"))
    await s.init()
    await s.insert_corpus(
        [
            {
                "id": "p1",
                "company_slug": "bds",
                "title": "Field Rep",
                "location": "NY",
                "full_text": "Text 1",
            },
            {
                "id": "p2",
                "company_slug": "troc",
                "title": "Sales Manager",
                "location": "CA",
                "full_text": "Text 2",
            },
        ]
    )
    yield s
    await s.close()


async def _create_run_with_results(
    store: EvalStore, model: str, prompt: str, results: dict[str, dict]
) -> int:
    """Helper: create a run with parsed results for given postings."""

    run_id = await store.create_run(1, model, prompt, len(results))
    for posting_id, parsed in results.items():
        await store.insert_result(run_id, posting_id, "{}", parsed, True, 100, 50, 0.001, 500)
    return run_id


# --- Type coercion tests ---


class TestCoerceType:
    def test_enum_normalizes(self):
        assert _coerce_type("role_archetype", '"Field_Rep"') == "field_rep"
        assert _coerce_type("role_archetype", "MANAGER") == "manager"

    def test_float_parses(self):
        assert _coerce_type("pay_min", "50000") == 50000.0
        assert _coerce_type("pay_min", '"55000.50"') == 55000.50
        assert _coerce_type("pay_min", "invalid") is None

    def test_bool_parses(self):
        assert _coerce_type("has_commission", "true") is True
        assert _coerce_type("has_commission", "False") is False
        assert _coerce_type("has_commission", "1") is True
        assert _coerce_type("has_commission", "0") is False

    def test_int_parses(self):
        assert _coerce_type("store_count", "5") == 5
        assert _coerce_type("store_count", '"10"') == 10
        assert _coerce_type("store_count", "invalid") is None

    def test_list_from_json(self):
        assert _coerce_type("tools_mentioned", '["Salesforce", "Repsly"]') == [
            "salesforce",
            "repsly",
        ]

    def test_list_from_comma_separated(self):
        assert _coerce_type("tools_mentioned", "Salesforce, Repsly") == [
            "salesforce",
            "repsly",
        ]

    def test_list_from_python_list(self):
        assert _coerce_type("tools_mentioned", ["Salesforce", "Repsly"]) == [
            "salesforce",
            "repsly",
        ]

    def test_none_passthrough(self):
        assert _coerce_type("role_archetype", None) is None
        assert _coerce_type("pay_min", None) is None


# --- Value comparison tests ---


class TestCompareValues:
    def test_enum_case_insensitive(self):
        assert _compare_values("role_archetype", "field_rep", "Field_Rep") is True
        assert _compare_values("role_archetype", "manager", "field_rep") is False

    def test_float_within_tolerance(self):
        assert _compare_values("pay_min", 50000, 50000) is True
        assert _compare_values("pay_min", 51000, 50000) is True  # 2% off
        assert _compare_values("pay_min", 55000, 50000) is False  # 10% off

    def test_float_zero_exact(self):
        assert _compare_values("pay_min", 0, 0) is True
        assert _compare_values("pay_min", 1, 0) is False

    def test_bool_exact(self):
        assert _compare_values("has_commission", True, True) is True
        assert _compare_values("has_commission", True, False) is False

    def test_int_exact(self):
        assert _compare_values("store_count", 5, 5) is True
        assert _compare_values("store_count", 5, 6) is False

    def test_list_jaccard(self):
        # 2/3 overlap = 0.67 >= 0.5 threshold
        assert (
            _compare_values(
                "tools_mentioned", ["salesforce", "repsly", "extra"], ["salesforce", "repsly"]
            )
            is True
        )
        # 0/5 overlap (Jaccard = 0.0) < 0.5 threshold
        assert (
            _compare_values(
                "tools_mentioned", ["salesforce", "other1", "other2"], ["repsly", "tableau"]
            )
            is False
        )

    def test_both_none(self):
        assert _compare_values("role_archetype", None, None) is True

    def test_one_none(self):
        assert _compare_values("role_archetype", None, "field_rep") is False
        assert _compare_values("role_archetype", "field_rep", None) is False


# --- Ground truth extraction tests ---


class TestExtractGroundTruth:
    async def test_correct_no_correction(self, store: EvalStore):
        """is_correct=1, no correct_value -> ground truth = model_value."""
        run_id = await _create_run_with_results(
            store, "haiku", "v1", {"p1": {"role_archetype": "field_rep"}}
        )
        await store.upsert_field_review(
            result_id=1, field_name="role_archetype", model_value='"field_rep"', is_correct=1
        )
        gt = await extract_ground_truth(store, run_id)
        assert ("p1", "role_archetype") in gt
        assert gt[("p1", "role_archetype")].ground_truth_value == "field_rep"
        assert gt[("p1", "role_archetype")].is_improvement is False

    async def test_improvement(self, store: EvalStore):
        """is_correct=1 with correct_value -> ground truth = improved value."""
        run_id = await _create_run_with_results(
            store, "haiku", "v1", {"p1": {"role_level": "entry"}}
        )
        await store.upsert_field_review(
            result_id=1,
            field_name="role_level",
            model_value='"entry"',
            is_correct=1,
            correct_value="junior",
        )
        gt = await extract_ground_truth(store, run_id)
        assert gt[("p1", "role_level")].ground_truth_value == "junior"
        assert gt[("p1", "role_level")].is_improvement is True

    async def test_wrong_with_correction(self, store: EvalStore):
        """is_correct=0, correct_value set -> ground truth = correction."""
        run_id = await _create_run_with_results(
            store, "haiku", "v1", {"p1": {"role_archetype": "manager"}}
        )
        await store.upsert_field_review(
            result_id=1,
            field_name="role_archetype",
            model_value='"manager"',
            is_correct=0,
            correct_value="team_lead",
        )
        gt = await extract_ground_truth(store, run_id)
        assert gt[("p1", "role_archetype")].ground_truth_value == "team_lead"

    async def test_skips_wrong_no_correction(self, store: EvalStore):
        """is_correct=0, no correct_value -> skip."""
        run_id = await _create_run_with_results(
            store, "haiku", "v1", {"p1": {"role_archetype": "manager"}}
        )
        await store.upsert_field_review(
            result_id=1,
            field_name="role_archetype",
            model_value='"manager"',
            is_correct=0,
        )
        gt = await extract_ground_truth(store, run_id)
        assert ("p1", "role_archetype") not in gt

    async def test_skips_cant_assess(self, store: EvalStore):
        """is_correct=-1 -> skip."""
        run_id = await _create_run_with_results(store, "haiku", "v1", {"p1": {"store_count": 5}})
        await store.upsert_field_review(
            result_id=1,
            field_name="store_count",
            model_value="5",
            is_correct=-1,
        )
        gt = await extract_ground_truth(store, run_id)
        assert ("p1", "store_count") not in gt


# --- Scoring pipeline tests ---


class TestScoring:
    async def test_scores_candidate_correctly(self, store: EvalStore):
        """Candidate values scored against ground truth."""
        # Baseline with reviews
        bl_run = await _create_run_with_results(
            store,
            "haiku",
            "v1",
            {
                "p1": {"role_archetype": "field_rep", "pay_min": 50000},
                "p2": {"role_archetype": "manager", "pay_min": 60000},
            },
        )
        # Review p1 as correct, p2 role_archetype as wrong
        results = await store.get_results(bl_run)
        for r in results:
            if r["posting_id"] == "p1":
                await store.upsert_field_review(r["id"], "role_archetype", '"field_rep"', 1)
                await store.upsert_field_review(r["id"], "pay_min", "50000", 1)
            else:
                await store.upsert_field_review(
                    r["id"], "role_archetype", '"manager"', 0, "team_lead"
                )
                await store.upsert_field_review(r["id"], "pay_min", "60000", 1)

        # Candidate run
        cand_run = await _create_run_with_results(
            store,
            "haiku",
            "v2",
            {
                "p1": {"role_archetype": "field_rep", "pay_min": 50000},
                "p2": {"role_archetype": "team_lead", "pay_min": 60000},
            },
        )

        gt = await extract_ground_truth(store, bl_run)
        scores, bl_acc = await score_candidate_run(store, gt, cand_run, bl_run)

        # All 4 fields should be correct in candidate
        assert all(s.is_correct for s in scores)

    async def test_regression_detection(self, store: EvalStore):
        """Baseline correct + candidate wrong -> is_regression=True."""
        bl_run = await _create_run_with_results(
            store, "haiku", "v1", {"p1": {"role_archetype": "field_rep"}}
        )
        results = await store.get_results(bl_run)
        await store.upsert_field_review(results[0]["id"], "role_archetype", '"field_rep"', 1)

        # Candidate gets it wrong
        cand_run = await _create_run_with_results(
            store, "haiku", "v2", {"p1": {"role_archetype": "manager"}}
        )

        gt = await extract_ground_truth(store, bl_run)
        scores, _ = await score_candidate_run(store, gt, cand_run, bl_run)

        assert len(scores) == 1
        assert scores[0].is_correct is False
        assert scores[0].is_regression is True
        assert scores[0].is_improvement is False


# --- Report assembly tests ---


class TestDiffReport:
    def test_error_pattern_aggregation(self):
        """Mismatch patterns grouped and counted correctly."""
        scores = [
            FieldScore(
                "p1",
                "role_archetype",
                "manager",
                "team_lead",
                False,
                False,
                False,
                "manager \u2192 team_lead",
            ),
            FieldScore(
                "p2",
                "role_archetype",
                "manager",
                "team_lead",
                False,
                False,
                False,
                "manager \u2192 team_lead",
            ),
            FieldScore("p1", "role_level", "entry", "mid", False, False, False, "entry \u2192 mid"),
            FieldScore("p2", "role_level", "mid", "mid", True, False, False, None),
        ]
        baseline_run = {"id": 1, "model": "haiku", "prompt_version": "v1"}
        candidate_run = {"id": 2, "model": "haiku", "prompt_version": "v2"}
        bl_accuracy = {"role_archetype": 0.5, "role_level": 0.5}

        report = compute_diff_report(scores, baseline_run, candidate_run, bl_accuracy)

        # Find role_archetype diff
        ra_diff = next(d for d in report.field_diffs if d.field_name == "role_archetype")
        assert ra_diff.candidate_accuracy == 0.0
        assert ra_diff.error_patterns == [("manager \u2192 team_lead", 2)]

        rl_diff = next(d for d in report.field_diffs if d.field_name == "role_level")
        assert rl_diff.candidate_accuracy == 0.5
        assert rl_diff.error_patterns == [("entry \u2192 mid", 1)]

    def test_confidence_intervals_present(self):
        """Wilson Score CIs computed for each field and overall."""
        scores = [
            FieldScore("p1", "role_archetype", "field_rep", "field_rep", True, False, False, None),
            FieldScore(
                "p2",
                "role_archetype",
                "manager",
                "field_rep",
                False,
                False,
                False,
                "manager \u2192 field_rep",
            ),
            FieldScore("p1", "pay_min", 50000, 50000, True, False, False, None),
            FieldScore("p2", "pay_min", 60000, 60000, True, False, False, None),
        ]
        baseline_run = {"id": 1, "model": "haiku", "prompt_version": "v1"}

        report = compute_diff_report(scores, baseline_run, None, None)

        # Per-field CIs
        ra_diff = next(d for d in report.field_diffs if d.field_name == "role_archetype")
        assert ra_diff.confidence_interval is not None
        lo, hi = ra_diff.confidence_interval
        assert 0.0 <= lo <= ra_diff.candidate_accuracy <= hi <= 1.0

        pm_diff = next(d for d in report.field_diffs if d.field_name == "pay_min")
        assert pm_diff.confidence_interval is not None
        # 2/2 correct — CI upper should be 1.0
        assert pm_diff.confidence_interval[1] == 1.0

        # Overall CI
        assert report.overall_confidence_interval is not None
        lo, hi = report.overall_confidence_interval
        assert 0.0 <= lo <= hi <= 1.0


# --- Wilson Score interval tests ---


class TestWilsonScoreInterval:
    def test_zero_total_returns_none(self):
        assert wilson_score_interval(0, 0) is None

    def test_perfect_score(self):
        lo, hi = wilson_score_interval(10, 10)
        assert hi == 1.0
        assert lo > 0.5  # 10/10 lower bound should be above 50%

    def test_zero_score(self):
        lo, hi = wilson_score_interval(0, 10)
        assert lo == 0.0
        assert hi < 0.5  # 0/10 upper bound should be below 50%

    def test_half_score(self):
        lo, hi = wilson_score_interval(5, 10)
        assert lo < 0.5
        assert hi > 0.5
        # CI should be centered near 0.5
        center = (lo + hi) / 2
        assert abs(center - 0.5) < 0.05

    def test_larger_sample_narrower_ci(self):
        """More data → narrower confidence interval."""
        ci_small = wilson_score_interval(8, 10)
        ci_large = wilson_score_interval(80, 100)
        assert ci_small is not None and ci_large is not None
        width_small = ci_small[1] - ci_small[0]
        width_large = ci_large[1] - ci_large[0]
        assert width_large < width_small

    def test_bounds_clamped(self):
        """CI bounds stay within [0, 1]."""
        lo, hi = wilson_score_interval(1, 1)
        assert lo >= 0.0
        assert hi <= 1.0

    def test_invalid_inputs_return_none(self):
        """Invalid inputs return None instead of crashing."""
        assert wilson_score_interval(-1, 10) is None
        assert wilson_score_interval(11, 10) is None
        assert wilson_score_interval(5, -1) is None
        assert wilson_score_interval(0, 0) is None
