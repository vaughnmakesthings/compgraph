#!/usr/bin/env python3
"""CLI tool for comparing prompt versions using ground truth from field reviews.

Usage:
    uv run python scripts/prompt_diff.py --baseline-run 2 --candidate-run 6
    uv run python scripts/prompt_diff.py --baseline pass1_v1 --candidate pass1_v2 --model haiku-3.5
    uv run python scripts/prompt_diff.py --baseline-run 2          # self-score mode
    uv run python scripts/prompt_diff.py --list-runs
    uv run python scripts/prompt_diff.py --baseline-run 2 --candidate-run 6 --export-csv diff.csv
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.ground_truth import (
    DiffReport,
    compute_diff_report,
    export_error_patterns_csv,
    extract_ground_truth,
    score_candidate_run,
)
from eval.store import EvalStore

DEFAULT_DB = str(Path(__file__).resolve().parent.parent / "data" / "eval.db")
DEFAULT_MIN_REVIEWS = 10


def _is_tty() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _color(text: str, code: str) -> str:
    if not _is_tty():
        return text
    return f"\033[{code}m{text}\033[0m"


def _green(text: str) -> str:
    return _color(text, "32")


def _red(text: str) -> str:
    return _color(text, "31")


def _gray(text: str) -> str:
    return _color(text, "90")


def _bold(text: str) -> str:
    return _color(text, "1")


def _format_pct(val: float | None) -> str:
    if val is None:
        return "  N/A "
    return f"{val * 100:5.1f}%"


def _format_ci(ci: tuple[float, float] | None) -> str:
    if ci is None:
        return ""
    return f"[{ci[0] * 100:.1f}%, {ci[1] * 100:.1f}%]"


def _format_delta(val: float | None) -> str:
    if val is None:
        return "      "
    pp = val * 100
    sign = "+" if pp > 0 else ""
    text = f"{sign}{pp:5.1f}pp"
    if pp > 0:
        return _green(text)
    elif pp < 0:
        return _red(text)
    return _gray(text)


async def list_runs(store: EvalStore) -> None:
    runs = await store.get_all_runs()
    reviewed_runs = await store.get_runs_with_reviews()
    reviewed_ids = {r["id"] for r in reviewed_runs}

    if not runs:
        print("No runs found.")
        return

    print(
        f"\n{'ID':>4}  {'Model':<20}  {'Prompt':<12}  {'Pass':>4}  {'Size':>5}  {'Reviews'}"
    )
    print("-" * 75)
    for r in runs:
        has_reviews = "*" if r["id"] in reviewed_ids else " "
        reviewed_count = await store.get_reviewed_count(r["id"])
        print(
            f"{r['id']:>4}  {r['model']:<20}  {r['prompt_version']:<12}  "
            f"{r['pass_number']:>4}  {r['corpus_size']:>5}  "
            f"{reviewed_count:>3} postings {has_reviews}"
        )
    print("\n* = has field reviews (can be used as baseline)")


def print_report(report: DiffReport, min_reviews: int) -> None:
    sep = "\u2550" * 62

    print(f"\n{sep}")
    print(_bold("CompGraph Prompt Diff"))
    if report.candidate_label:
        print(f"Baseline:  {report.baseline_label}  (run #{report.baseline_run_id})")
        print(f"Candidate: {report.candidate_label}  (run #{report.candidate_run_id})")
    else:
        print(f"Self-score: {report.baseline_label}  (run #{report.baseline_run_id})")

    total_fields = sum(d.reviewed_count for d in report.field_diffs)
    print(
        f"Ground truth: {report.reviewed_posting_count} postings, {total_fields} fields"
    )
    print(sep)

    if report.threshold_warning:
        print(
            f"\n{_red('!')} Only {report.reviewed_posting_count} postings reviewed "
            f"(min: {min_reviews}). Results may not generalize."
        )

    # Overall accuracy
    ci_str = ""
    if report.overall_confidence_interval:
        ci_str = f"  95% CI: {_format_ci(report.overall_confidence_interval)}"
    if report.candidate_label and report.overall_delta is not None:
        print(
            f"\nOverall: {_format_pct(report.overall_baseline_accuracy)} -> "
            f"{_format_pct(report.overall_candidate_accuracy)}  "
            f"({_format_delta(report.overall_delta)}){ci_str}"
        )
    elif report.overall_candidate_accuracy is not None:
        print(
            f"\nOverall accuracy: {_format_pct(report.overall_candidate_accuracy)}{ci_str}"
        )

    # Per-field table
    if report.candidate_label:
        print(
            f"\n{'Field':<20}  {'Baseline':>8}  {'Candidate':>9}  "
            f"{'Delta':>9}  {'N':>3}  {'R':>2}  {'I':>2}  {'95% CI'}"
        )
        print("\u2500" * 80)
    else:
        print(f"\n{'Field':<20}  {'Accuracy':>8}  {'N':>3}  {'95% CI'}")
        print("\u2500" * 56)

    for d in report.field_diffs:
        regressed = d.delta is not None and d.delta < 0
        suffix = f"  {_red('<- REGRESSED')}" if regressed else ""
        field_ci = _format_ci(d.confidence_interval)

        if report.candidate_label:
            print(
                f"{d.field_name:<20}  {_format_pct(d.baseline_accuracy):>8}  "
                f"{_format_pct(d.candidate_accuracy):>9}  "
                f"{_format_delta(d.delta):>9}  {d.reviewed_count:>3}  "
                f"{d.regressions:>2}  {d.improvements:>2}  {field_ci}{suffix}"
            )
        else:
            print(
                f"{d.field_name:<20}  {_format_pct(d.candidate_accuracy):>8}  "
                f"{d.reviewed_count:>3}  {field_ci}"
            )

    # Error patterns
    any_errors = any(d.error_patterns for d in report.field_diffs)
    if any_errors:
        print(f"\n{_bold('Error Patterns:')}")
        for d in report.field_diffs:
            for pattern, count in d.error_patterns[:3]:
                print(f'  {d.field_name}: "{pattern}" x{count}')

    print(sep)


async def run_diff(args: argparse.Namespace) -> None:
    store = EvalStore(args.db)
    await store.init()

    try:
        if args.list_runs:
            await list_runs(store)
            return

        # Resolve baseline run
        baseline_run = None
        if args.baseline_run:
            baseline_run = await store.get_run(args.baseline_run)
            if not baseline_run:
                print(
                    f"Error: baseline run #{args.baseline_run} not found.",
                    file=sys.stderr,
                )
                sys.exit(1)
        elif args.baseline:
            baseline_run = await store.find_run(
                pass_number=args.pass_number,
                model=args.model,
                prompt_version=args.baseline,
            )
            if not baseline_run:
                print(
                    f"Error: no run found for {args.model}/{args.baseline} pass {args.pass_number}.",
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            print("Error: --baseline-run or --baseline required.", file=sys.stderr)
            sys.exit(1)

        # Resolve candidate run
        candidate_run = None
        if args.candidate_run:
            candidate_run = await store.get_run(args.candidate_run)
            if not candidate_run:
                print(
                    f"Error: candidate run #{args.candidate_run} not found.",
                    file=sys.stderr,
                )
                sys.exit(1)
        elif args.candidate:
            candidate_run = await store.find_run(
                pass_number=args.pass_number,
                model=args.model,
                prompt_version=args.candidate,
            )
            if not candidate_run:
                print(
                    f"Error: no run found for {args.model}/{args.candidate} "
                    f"pass {args.pass_number}.",
                    file=sys.stderr,
                )
                sys.exit(1)

        # Extract ground truth from baseline reviews
        ground_truth = await extract_ground_truth(store, baseline_run["id"])
        if not ground_truth:
            print(
                f"Error: no usable field reviews found for run #{baseline_run['id']}. "
                "Review some postings first.",
                file=sys.stderr,
            )
            sys.exit(1)

        # Score
        if candidate_run:
            # Diff mode: score candidate against baseline ground truth
            scores, bl_accuracy = await score_candidate_run(
                store, ground_truth, candidate_run["id"], baseline_run["id"]
            )
            report = compute_diff_report(
                scores,
                baseline_run,
                candidate_run,
                bl_accuracy,
                min_reviews=args.min_reviews,
            )
        else:
            # Self-score mode: score baseline against its own ground truth
            scores, _ = await score_candidate_run(
                store, ground_truth, baseline_run["id"]
            )
            report = compute_diff_report(
                scores,
                baseline_run,
                None,
                None,
                min_reviews=args.min_reviews,
            )

        print_report(report, args.min_reviews)

        # CSV export
        if args.export_csv:
            csv_content = export_error_patterns_csv(report)
            Path(args.export_csv).write_text(csv_content)
            print(f"\nError patterns exported to {args.export_csv}")

    finally:
        await store.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare prompt versions using ground truth from field reviews."
    )
    parser.add_argument("--baseline-run", type=int, help="Baseline run ID")
    parser.add_argument("--candidate-run", type=int, help="Candidate run ID")
    parser.add_argument("--baseline", help="Baseline prompt version (e.g., pass1_v1)")
    parser.add_argument("--candidate", help="Candidate prompt version (e.g., pass1_v2)")
    parser.add_argument(
        "--model", default="haiku-3.5", help="Model name (default: haiku-3.5)"
    )
    parser.add_argument(
        "--pass-number", type=int, default=1, help="Pass number (default: 1)"
    )
    parser.add_argument("--export-csv", help="Export error patterns to CSV file")
    parser.add_argument(
        "--list-runs", action="store_true", help="List all runs and exit"
    )
    parser.add_argument("--db", default=DEFAULT_DB, help="Database path")
    parser.add_argument(
        "--min-reviews",
        type=int,
        default=DEFAULT_MIN_REVIEWS,
        help="Minimum reviewed postings threshold (default: 10)",
    )

    args = parser.parse_args()
    asyncio.run(run_diff(args))


if __name__ == "__main__":
    main()
