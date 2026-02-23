"""Ground truth extraction, type-aware scoring, and diff reporting for prompt evaluation."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from typing import Any

REVIEWABLE_FIELDS = [
    "role_archetype",
    "role_level",
    "employment_type",
    "pay_type",
    "pay_min",
    "pay_max",
    "pay_frequency",
    "has_commission",
    "has_benefits",
    "travel_required",
    "tools_mentioned",
    "kpis_mentioned",
    "store_count",
]

FIELD_TYPES: dict[str, str] = {
    "role_archetype": "enum",
    "role_level": "enum",
    "employment_type": "enum",
    "pay_type": "enum",
    "pay_frequency": "enum",
    "pay_min": "float",
    "pay_max": "float",
    "has_commission": "bool",
    "has_benefits": "bool",
    "travel_required": "bool",
    "store_count": "int",
    "tools_mentioned": "list",
    "kpis_mentioned": "list",
}

PAY_TOLERANCE = 0.05  # ±5% for float comparison
LIST_JACCARD_THRESHOLD = 0.5  # 50% set overlap for list fields

WILSON_Z = 1.96  # z-score for 95% confidence interval


# --- Confidence intervals ---


def wilson_score_interval(successes: int, total: int) -> tuple[float, float] | None:
    """Compute Wilson Score 95% confidence interval for a proportion.

    More accurate than normal approximation for small samples.
    Returns (lower, upper) or None if inputs are invalid.
    """
    if total <= 0 or successes < 0 or successes > total:
        return None
    import math

    p = successes / total
    z = WILSON_Z
    z2 = z * z
    denom = 1 + z2 / total
    center = (p + z2 / (2 * total)) / denom
    margin = z / denom * math.sqrt(p * (1 - p) / total + z2 / (4 * total * total))
    return (max(0.0, center - margin), min(1.0, center + margin))


# --- Data structures ---


@dataclass
class GroundTruthEntry:
    posting_id: str
    field_name: str
    ground_truth_value: Any  # Python-typed, not JSON string
    source_run_id: int
    is_improvement: bool  # True when is_correct=1 + correct_value set


@dataclass
class FieldScore:
    posting_id: str
    field_name: str
    candidate_value: Any
    ground_truth_value: Any
    is_correct: bool
    is_regression: bool  # was correct in baseline, wrong in candidate
    is_improvement: bool  # was wrong in baseline, correct in candidate
    mismatch_pattern: str | None  # e.g. "manager → team_lead"


@dataclass
class FieldDiff:
    field_name: str
    baseline_accuracy: float | None
    candidate_accuracy: float
    delta: float | None
    reviewed_count: int
    regressions: int
    improvements: int
    error_patterns: list[tuple[str, int]]  # [("manager→team_lead", 3)]
    confidence_interval: tuple[float, float] | None = None  # Wilson Score 95% CI


@dataclass
class DiffReport:
    baseline_run_id: int
    candidate_run_id: int | None
    baseline_label: str  # "haiku-3.5/pass1_v1"
    candidate_label: str | None
    reviewed_posting_count: int
    threshold_warning: bool  # True if < 10 reviewed postings
    field_diffs: list[FieldDiff]
    overall_baseline_accuracy: float | None
    overall_candidate_accuracy: float | None
    overall_delta: float | None
    overall_confidence_interval: tuple[float, float] | None = None  # Wilson Score 95% CI


# --- Type coercion ---


def _coerce_type(field_name: str, raw_value: Any) -> Any:
    """Coerce a raw value (from JSON string or reviewer text) to the correct Python type."""
    if raw_value is None:
        return None

    field_type = FIELD_TYPES.get(field_name, "enum")

    if field_type == "enum":
        return str(raw_value).lower().strip().strip('"')

    if field_type == "float":
        try:
            return float(str(raw_value).strip().strip('"'))
        except (ValueError, TypeError):
            return None

    if field_type == "bool":
        v = str(raw_value).lower().strip().strip('"')
        if v in ("true", "1", "yes"):
            return True
        if v in ("false", "0", "no"):
            return False
        return None

    if field_type == "int":
        try:
            return int(float(str(raw_value).strip().strip('"')))
        except (ValueError, TypeError):
            return None

    if field_type == "list":
        if isinstance(raw_value, list):
            return [str(x).lower().strip() for x in raw_value]
        s = str(raw_value).strip()
        # Try JSON parse first
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(x).lower().strip() for x in parsed]
        except (json.JSONDecodeError, TypeError):
            pass
        # Comma-separated fallback for reviewer input like "salesforce, repsly"
        if "," in s:
            s = s.strip("[]")
            return [x.strip().lower().strip('"') for x in s.split(",") if x.strip()]
        # Single item
        if s and s != "[]":
            return [s.lower().strip('"')]
        return []

    return raw_value


# --- Value comparison ---


def _compare_values(field_name: str, candidate: Any, ground_truth: Any) -> bool:
    """Compare candidate value against ground truth using type-appropriate strategy."""
    if candidate is None and ground_truth is None:
        return True
    if candidate is None or ground_truth is None:
        return False

    field_type = FIELD_TYPES.get(field_name, "enum")

    if field_type == "enum":
        return str(candidate).lower().strip() == str(ground_truth).lower().strip()

    if field_type == "float":
        try:
            c, g = float(candidate), float(ground_truth)
        except (ValueError, TypeError):
            return False
        if g == 0:
            return c == 0
        return abs(c - g) / abs(g) <= PAY_TOLERANCE

    if field_type == "bool":
        return bool(candidate) == bool(ground_truth)

    if field_type == "int":
        try:
            return int(candidate) == int(ground_truth)
        except (ValueError, TypeError):
            return False

    if field_type == "list":
        c_set = set(candidate) if isinstance(candidate, list) else set()
        g_set = set(ground_truth) if isinstance(ground_truth, list) else set()
        if not c_set and not g_set:
            return True
        if not c_set or not g_set:
            return False
        intersection = c_set & g_set
        union = c_set | g_set
        return len(intersection) / len(union) >= LIST_JACCARD_THRESHOLD

    return candidate == ground_truth


# --- Ground truth extraction ---


async def extract_ground_truth(
    store: Any, source_run_id: int
) -> dict[tuple[str, str], GroundTruthEntry]:
    """Extract ground truth from field_reviews for a run.

    Resolution rules:
    - is_correct=1, correct_value=NULL → ground truth = model_value
    - is_correct=1, correct_value=X → ground truth = X (improvement is the ideal)
    - is_correct=0, correct_value=X → ground truth = X (human correction)
    - is_correct=0, correct_value=NULL → skip (wrong but no correction)
    - is_correct=-1 → skip (can't assess)
    """
    all_reviews = await store.get_all_field_reviews_for_run(source_run_id)
    results = await store.get_results(source_run_id)
    result_map = {r["id"]: r for r in results}

    ground_truth: dict[tuple[str, str], GroundTruthEntry] = {}

    for result_id, reviews in all_reviews.items():
        result = result_map.get(result_id)
        if not result:
            continue
        posting_id = result["posting_id"]

        for review in reviews:
            field_name = review["field_name"]
            is_correct = review["is_correct"]
            correct_value = review.get("correct_value")
            model_value = review.get("model_value")

            # Skip can't assess
            if is_correct == -1:
                continue

            # Skip wrong without correction
            if is_correct == 0 and correct_value is None:
                continue

            is_improvement = False
            if is_correct == 1 and correct_value is not None:
                # Improvement — use the improved value
                raw_gt = correct_value
                is_improvement = True
            elif is_correct == 1:
                # Correct as-is — use model value
                raw_gt = model_value
            else:
                # Wrong with correction
                raw_gt = correct_value

            gt_value = _coerce_type(field_name, raw_gt)
            ground_truth[(posting_id, field_name)] = GroundTruthEntry(
                posting_id=posting_id,
                field_name=field_name,
                ground_truth_value=gt_value,
                source_run_id=source_run_id,
                is_improvement=is_improvement,
            )

    return ground_truth


# --- Scoring pipeline ---


async def score_candidate_run(
    store: Any,
    ground_truth: dict[tuple[str, str], GroundTruthEntry],
    candidate_run_id: int,
    baseline_run_id: int | None = None,
) -> tuple[list[FieldScore], dict[str, float] | None]:
    """Score a candidate run against ground truth.

    Returns (field_scores, baseline_field_accuracy_or_none).
    """
    candidate_results = await store.get_results(candidate_run_id)

    # Build candidate lookup: posting_id → parsed fields
    candidate_lookup: dict[str, dict] = {}
    for r in candidate_results:
        parsed = r.get("parsed_result")
        if parsed:
            if isinstance(parsed, str):
                try:
                    parsed = json.loads(parsed)
                except json.JSONDecodeError:
                    continue
            candidate_lookup[r["posting_id"]] = parsed

    # If baseline provided, also score it for regression detection
    baseline_scores: dict[tuple[str, str], bool] | None = None
    if baseline_run_id is not None:
        baseline_results = await store.get_results(baseline_run_id)
        baseline_lookup: dict[str, dict] = {}
        for r in baseline_results:
            parsed = r.get("parsed_result")
            if parsed:
                if isinstance(parsed, str):
                    try:
                        parsed = json.loads(parsed)
                    except json.JSONDecodeError:
                        continue
                baseline_lookup[r["posting_id"]] = parsed

        baseline_scores = {}
        for (posting_id, field_name), gt_entry in ground_truth.items():
            if posting_id in baseline_lookup:
                bl_raw = baseline_lookup[posting_id].get(field_name)
                bl_val = _coerce_type(field_name, bl_raw)
                baseline_scores[(posting_id, field_name)] = _compare_values(
                    field_name, bl_val, gt_entry.ground_truth_value
                )

    # Score candidate
    field_scores: list[FieldScore] = []
    for (posting_id, field_name), gt_entry in ground_truth.items():
        if posting_id not in candidate_lookup:
            continue

        cand_raw = candidate_lookup[posting_id].get(field_name)
        cand_val = _coerce_type(field_name, cand_raw)
        is_correct = _compare_values(field_name, cand_val, gt_entry.ground_truth_value)

        is_regression = False
        is_improvement = False
        if baseline_scores is not None:
            bl_correct = baseline_scores.get((posting_id, field_name))
            if bl_correct is not None:
                is_regression = bl_correct and not is_correct
                is_improvement = not bl_correct and is_correct

        mismatch_pattern = None
        if not is_correct:
            cand_display = _format_value(cand_val)
            gt_display = _format_value(gt_entry.ground_truth_value)
            mismatch_pattern = f"{cand_display} \u2192 {gt_display}"

        field_scores.append(
            FieldScore(
                posting_id=posting_id,
                field_name=field_name,
                candidate_value=cand_val,
                ground_truth_value=gt_entry.ground_truth_value,
                is_correct=is_correct,
                is_regression=is_regression,
                is_improvement=is_improvement,
                mismatch_pattern=mismatch_pattern,
            )
        )

    # Compute baseline field accuracy if baseline was scored
    baseline_field_accuracy: dict[str, float] | None = None
    if baseline_scores is not None:
        from collections import defaultdict

        bl_counts: dict[str, list[bool]] = defaultdict(list)
        for (_, field_name), correct in baseline_scores.items():
            bl_counts[field_name].append(correct)
        baseline_field_accuracy = {
            fn: sum(vals) / len(vals) for fn, vals in bl_counts.items() if vals
        }

    return field_scores, baseline_field_accuracy


def _format_value(val: Any) -> str:
    """Format a value for display in mismatch patterns."""
    if val is None:
        return "null"
    if isinstance(val, list):
        return json.dumps(val) if val else "[]"
    if isinstance(val, bool):
        return str(val).lower()
    return str(val)


# --- Report assembly ---


def compute_diff_report(
    scores: list[FieldScore],
    baseline_run: dict,
    candidate_run: dict | None,
    baseline_field_accuracy: dict[str, float] | None,
    *,
    min_reviews: int = 10,
) -> DiffReport:
    """Aggregate FieldScores into a DiffReport."""
    from collections import Counter, defaultdict

    # Group scores by field
    by_field: dict[str, list[FieldScore]] = defaultdict(list)
    posting_ids: set[str] = set()
    for s in scores:
        by_field[s.field_name].append(s)
        posting_ids.add(s.posting_id)

    field_diffs: list[FieldDiff] = []
    total_correct = 0
    total_scored = 0

    for field_name in REVIEWABLE_FIELDS:
        field_scores = by_field.get(field_name, [])
        if not field_scores:
            continue

        correct_count = sum(1 for s in field_scores if s.is_correct)
        candidate_acc = correct_count / len(field_scores)
        bl_acc = baseline_field_accuracy.get(field_name) if baseline_field_accuracy else None
        delta = (candidate_acc - bl_acc) if bl_acc is not None else None

        regressions = sum(1 for s in field_scores if s.is_regression)
        improvements = sum(1 for s in field_scores if s.is_improvement)

        # Error pattern frequency
        pattern_counter: Counter[str] = Counter()
        for s in field_scores:
            if s.mismatch_pattern:
                pattern_counter[s.mismatch_pattern] += 1
        error_patterns = pattern_counter.most_common()

        field_diffs.append(
            FieldDiff(
                field_name=field_name,
                baseline_accuracy=bl_acc,
                candidate_accuracy=candidate_acc,
                delta=delta,
                reviewed_count=len(field_scores),
                regressions=regressions,
                improvements=improvements,
                error_patterns=error_patterns,
                confidence_interval=wilson_score_interval(correct_count, len(field_scores)),
            )
        )

        total_correct += correct_count
        total_scored += len(field_scores)

    overall_candidate = total_correct / total_scored if total_scored else None

    total_bl_correct = sum(
        d.baseline_accuracy * d.reviewed_count
        for d in field_diffs
        if d.baseline_accuracy is not None
    )
    total_bl_scored = sum(d.reviewed_count for d in field_diffs if d.baseline_accuracy is not None)
    overall_baseline = total_bl_correct / total_bl_scored if total_bl_scored else None

    overall_delta = None
    if overall_candidate is not None and overall_baseline is not None:
        overall_delta = overall_candidate - overall_baseline

    baseline_label = f"{baseline_run['model']}/{baseline_run['prompt_version']}"
    candidate_label = (
        f"{candidate_run['model']}/{candidate_run['prompt_version']}" if candidate_run else None
    )

    return DiffReport(
        baseline_run_id=baseline_run["id"],
        candidate_run_id=candidate_run["id"] if candidate_run else None,
        baseline_label=baseline_label,
        candidate_label=candidate_label,
        reviewed_posting_count=len(posting_ids),
        threshold_warning=len(posting_ids) < min_reviews,
        field_diffs=field_diffs,
        overall_baseline_accuracy=overall_baseline,
        overall_candidate_accuracy=overall_candidate,
        overall_delta=overall_delta,
        overall_confidence_interval=wilson_score_interval(total_correct, total_scored),
    )


# --- CSV export ---


def export_error_patterns_csv(report: DiffReport) -> str:
    """Export error patterns to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["field_name", "pattern", "count", "candidate_accuracy", "baseline_accuracy", "delta"]
    )

    for diff in report.field_diffs:
        for pattern, count in diff.error_patterns:
            writer.writerow(
                [
                    diff.field_name,
                    pattern,
                    count,
                    f"{diff.candidate_accuracy:.3f}",
                    f"{diff.baseline_accuracy:.3f}" if diff.baseline_accuracy is not None else "",
                    f"{diff.delta:.3f}" if diff.delta is not None else "",
                ]
            )

    return output.getvalue()
