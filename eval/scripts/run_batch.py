"""Batch evaluation runner — run all models and generate a report.

Usage:
    cd compgraph-eval
    op run --env-file=../.env -- uv run python scripts/run_batch.py [OPTIONS]

    --pass-number INT   Pass to evaluate (default: 1)
    --prompt TEXT        Prompt version (default: pass1_v1)
    --models TEXT        Comma-separated aliases (default: all)
    --concurrency INT   Max parallel LLM calls per model (default: 5)
    --corpus TEXT        Path to corpus.json (default: data/corpus.json)
    --db TEXT            Path to eval.db (default: data/eval.db)
    --force             Re-run even if results exist
    --report-only       Skip running, just report on existing results
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.config import MODELS
from eval.runner import RunSummary, load_corpus, run_evaluation
from eval.store import EvalStore
from eval.validator import validate_run

DATA_DIR = Path(__file__).parent.parent / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch evaluation runner")
    parser.add_argument(
        "--pass-number", type=int, default=1, help="Pass to evaluate (1 or 2)"
    )
    parser.add_argument("--prompt", default="pass1_v1", help="Prompt version")
    parser.add_argument(
        "--models", default=None, help="Comma-separated model aliases (default: all)"
    )
    parser.add_argument(
        "--concurrency", type=int, default=5, help="Max parallel LLM calls per model"
    )
    parser.add_argument(
        "--corpus", default=str(DATA_DIR / "corpus.json"), help="Path to corpus.json"
    )
    parser.add_argument(
        "--db", default=str(DATA_DIR / "eval.db"), help="Path to eval.db"
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-run even if results exist"
    )
    parser.add_argument(
        "--report-only", action="store_true", help="Skip running, just report"
    )
    return parser.parse_args()


def get_model_list(models_arg: str | None) -> list[str]:
    if models_arg:
        aliases = [m.strip() for m in models_arg.split(",")]
        for alias in aliases:
            if alias not in MODELS:
                print(
                    f"ERROR: Unknown model alias '{alias}'. Available: {', '.join(MODELS.keys())}"
                )
                sys.exit(1)
        return aliases
    return list(MODELS.keys())


def make_progress_callback(model: str, total: int):
    """Create a progress callback that prints inline progress."""

    def callback(completed: int, total_count: int):
        pct = completed / total_count * 100 if total_count > 0 else 0
        bar_len = 30
        filled = int(bar_len * completed / total_count) if total_count > 0 else 0
        bar = "━" * filled + "░" * (bar_len - filled)
        print(
            f"\r  {model}: {bar} {completed}/{total_count} ({pct:.0f}%)",
            end="",
            flush=True,
        )

    return callback


async def run_batch(args: argparse.Namespace) -> None:
    store = EvalStore(args.db)
    await store.init()

    model_list = get_model_list(args.models)

    # Load corpus to get size for report header
    corpus_path = Path(args.corpus)
    if not corpus_path.exists():
        print(f"ERROR: Corpus file not found: {args.corpus}")
        await store.close()
        sys.exit(1)
    corpus = load_corpus(args.corpus)
    corpus_size = len(corpus)

    summaries: dict[str, RunSummary] = {}
    run_ids: dict[str, int] = {}

    if not args.report_only:
        print(
            f"\nRunning Pass {args.pass_number} | Prompt: {args.prompt} | Corpus: {corpus_size} postings"
        )
        print(f"Models: {', '.join(model_list)}\n")

        for model in model_list:
            existing = await store.find_run(args.pass_number, model, args.prompt)
            if existing and not args.force:
                print(
                    f"  {model}: skipped (run #{existing['id']} exists, use --force to re-run)"
                )
                run_ids[model] = existing["id"]
                # Build summary from existing run
                summaries[model] = RunSummary(
                    run_id=existing["id"],
                    total=existing["corpus_size"],
                    total_cost_usd=existing.get("total_cost_usd") or 0.0,
                    total_duration_ms=existing.get("total_duration_ms") or 0,
                    total_input_tokens=existing.get("total_input_tokens") or 0,
                    total_output_tokens=existing.get("total_output_tokens") or 0,
                )
                results = await store.get_results(existing["id"])
                summaries[model].succeeded = sum(
                    1 for r in results if r["parse_success"]
                )
                summaries[model].failed = len(results) - summaries[model].succeeded
                continue

            print(f"  {model}: running...")
            progress_cb = make_progress_callback(model, corpus_size)
            summary = await run_evaluation(
                store=store,
                pass_number=args.pass_number,
                model=model,
                prompt_version=args.prompt,
                corpus_path=args.corpus,
                concurrency=args.concurrency,
                on_progress=progress_cb,
            )
            print()  # newline after progress bar
            summaries[model] = summary
            run_ids[model] = summary.run_id
    else:
        # Report-only: load existing runs
        for model in model_list:
            existing = await store.find_run(args.pass_number, model, args.prompt)
            if existing:
                run_ids[model] = existing["id"]
                summaries[model] = RunSummary(
                    run_id=existing["id"],
                    total=existing["corpus_size"],
                    total_cost_usd=existing.get("total_cost_usd") or 0.0,
                    total_duration_ms=existing.get("total_duration_ms") or 0,
                    total_input_tokens=existing.get("total_input_tokens") or 0,
                    total_output_tokens=existing.get("total_output_tokens") or 0,
                )
                results = await store.get_results(existing["id"])
                summaries[model].succeeded = sum(
                    1 for r in results if r["parse_success"]
                )
                summaries[model].failed = len(results) - summaries[model].succeeded

    # Validate and collect accuracy data
    validations: dict[str, float] = {}
    all_violations: list[tuple[str, str, str, int]] = []  # (model, field, value, count)
    accuracy_data: dict[
        str, tuple[float, int, int]
    ] = {}  # model -> (accuracy, reviewed, total)

    for model in model_list:
        if model not in run_ids:
            continue
        rid = run_ids[model]
        validation = await validate_run(store, rid)
        validations[model] = validation.compliance_rate
        for field_name, value, count in validation.common_violations[:5]:
            all_violations.append((model, field_name, value, count))

        # Check for human review data
        reviewed = await store.get_reviewed_count(rid)
        if reviewed > 0:
            field_acc = await store.get_field_accuracy(rid)
            if field_acc:
                avg_acc = sum(field_acc.values()) / len(field_acc)
                results = await store.get_results(rid)
                accuracy_data[model] = (avg_acc, reviewed, len(results))

    # Print report
    print_report(
        args,
        corpus_size,
        model_list,
        summaries,
        validations,
        all_violations,
        accuracy_data,
    )

    await store.close()


def print_report(
    args: argparse.Namespace,
    corpus_size: int,
    model_list: list[str],
    summaries: dict[str, RunSummary],
    validations: dict[str, float],
    all_violations: list[tuple[str, str, str, int]],
    accuracy_data: dict[str, tuple[float, int, int]],
) -> None:
    sep = "=" * 70
    thin = "─" * 70

    print(f"\n{sep}")
    print("CompGraph Eval — Batch Report")
    print(
        f"Pass {args.pass_number} | Prompt: {args.prompt} | Corpus: {corpus_size} postings"
    )
    print(sep)

    if not summaries:
        print("\nNo runs found.")
        print(sep)
        return

    # Build leaderboard rows
    rows = []
    for model in model_list:
        if model not in summaries:
            continue
        s = summaries[model]
        parse_pct = f"{s.succeeded / s.total * 100:.0f}%" if s.total > 0 else "—"
        comply_pct = (
            f"{validations.get(model, 0) * 100:.0f}%" if model in validations else "—"
        )

        if model in accuracy_data:
            acc, reviewed, total = accuracy_data[model]
            acc_str = f"{acc * 100:.0f}%*"
        else:
            acc_str = "—"

        cost_str = f"${s.total_cost_usd:.4f}"
        latency_str = f"{s.total_duration_ms / 1000:.1f}s"
        rows.append((model, parse_pct, comply_pct, acc_str, cost_str, latency_str))

    # Sort by compliance then parse rate
    def sort_key(row):
        comply = float(row[2].rstrip("%*")) if row[2] not in ("—",) else 0
        parse = float(row[1].rstrip("%*")) if row[1] not in ("—",) else 0
        return (comply, parse)

    rows.sort(key=sort_key, reverse=True)

    # Print table
    print(
        f"\n{'Rank':<6}{'Model':<16}{'Parse%':<8}{'Comply%':<9}{'Accuracy':<10}{'Cost':<10}{'Latency':<8}"
    )
    print(
        f"{'────':<6}{'─' * 15:<16}{'──────':<8}{'───────':<9}{'────────':<10}{'────────':<10}{'───────':<8}"
    )

    for i, (model, parse, comply, acc, cost, latency) in enumerate(rows, 1):
        print(f" {i:<5}{model:<16}{parse:<8}{comply:<9}{acc:<10}{cost:<10}{latency:<8}")

    # Accuracy footnote
    if accuracy_data:
        print()
        for model, (acc, reviewed, total) in accuracy_data.items():
            print(
                f"* Accuracy from human reviews ({reviewed}/{total} postings reviewed)"
            )
        print("— = no human reviews yet")

    # Schema violations
    if all_violations:
        print(f"\n{thin}")
        print("Schema Violations (top 5):")
        sorted_v = sorted(all_violations, key=lambda x: x[3], reverse=True)[:5]
        for model, field_name, value, count in sorted_v:
            print(f"  {model}: {field_name}={json.dumps(value)} (x{count})")

    # Cost efficiency
    print(f"\n{thin}")
    print("Cost Efficiency (compliance-adjusted parse rate per $0.01):")
    efficiency = []
    for model in model_list:
        if model not in summaries:
            continue
        s = summaries[model]
        comply = validations.get(model, 0)
        if s.total_cost_usd > 0 and s.total > 0:
            rate = (s.succeeded / s.total) * comply / (s.total_cost_usd / 0.01)
            efficiency.append((model, rate))
    efficiency.sort(key=lambda x: x[1], reverse=True)
    for i, (model, rate) in enumerate(efficiency, 1):
        print(f" {i}  {model:<20}{rate:.1f} parses/$0.01")

    print(sep)


def main():
    args = parse_args()
    asyncio.run(run_batch(args))


if __name__ == "__main__":
    main()
