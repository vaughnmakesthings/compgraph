#!/usr/bin/env python3
"""Analyze eval errors and suggest prompt improvements via a single LLM call.

Pulls all field reviews from the eval DB, pairs each error with its posting text
and model output, then asks an LLM to classify errors and generate prompt patches.

Usage:
    uv run python scripts/analyze_errors.py
    uv run python scripts/analyze_errors.py --model sonnet-4 --run-id 2
    uv run python scripts/analyze_errors.py --output patches.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.config import MODELS
from eval.ground_truth import FIELD_TYPES
from eval.prompts.pass1_v1 import SYSTEM_PROMPT as PASS1_PROMPT
from eval.providers import call_llm
from eval.store import EvalStore

DEFAULT_DB = str(Path(__file__).resolve().parent.parent / "data" / "eval.db")
DEFAULT_MODEL = "opus-4.6"

ERROR_TAXONOMY = """\
| Error Type        | Description                        |
|-------------------|------------------------------------|
| Misclassification | Correct structure, wrong value     |
| Hallucination     | Value not in source text           |
| Omission          | Failed to extract existing value   |
| Boundary Error    | Numeric partially correct          |
| Type Error        | Wrong data type or format          |
| Granularity Error | Wrong specificity level            |
| Conflation        | Merged distinct values             |
| Source Confusion   | Extracted from wrong section       |
| Temporal Error    | Outdated or conditional value      |"""


def _build_analysis_prompt(
    errors: list[dict],
    correct_summary: dict[str, int],
    current_prompt: str,
) -> str:
    """Build the user message for the analysis LLM call."""
    parts = []

    parts.append("# Prompt Optimization Analysis\n")
    parts.append(
        "You are analyzing a job posting extraction prompt. "
        "Your goal: classify each error, find patterns, and produce a patched prompt.\n"
    )

    # Current prompt
    parts.append("## Current System Prompt\n")
    parts.append(f"```\n{current_prompt}\n```\n")

    # Correct field summary
    parts.append("## Fields the Model Gets Right\n")
    for field, count in sorted(correct_summary.items(), key=lambda x: -x[1]):
        parts.append(f"- {field}: {count} correct")
    parts.append("")

    # Error taxonomy
    parts.append("## Error Taxonomy\n")
    parts.append(ERROR_TAXONOMY)
    parts.append("")

    # Errors
    parts.append(f"## Extraction Errors ({len(errors)} total)\n")
    for i, err in enumerate(errors, 1):
        parts.append(
            f"### Error {i}: `{err['field_name']}` on posting `{err['posting_id']}`\n"
        )
        parts.append(f"**Title:** {err['title']}")
        parts.append(f"**Field type:** {FIELD_TYPES.get(err['field_name'], 'unknown')}")
        parts.append(f"**Model output:** `{err['model_value']}`")
        parts.append(f"**Correct value:** `{err['correct_value']}`")
        parts.append(
            f"**Type:** {err['review_type']} (improvement = acceptable but better value exists; error = wrong)"
        )
        parts.append("\n**Posting text** (truncated to 2000 chars):\n")
        text = err["full_text"][:2000]
        parts.append(f"```\n{text}\n```\n")

    # Instructions
    parts.append("## Your Task\n")
    parts.append(
        "Analyze the errors above and produce a JSON response with exactly these keys:\n"
    )
    parts.append("""```json
{
  "classified_errors": [
    {
      "error_num": 1,
      "field": "role_archetype",
      "error_type": "Misclassification",
      "explanation": "Why this error happened based on the posting text",
      "root_cause": "What in the prompt caused or failed to prevent this"
    }
  ],
  "patterns": [
    {
      "error_type": "Misclassification",
      "count": 3,
      "fields_affected": ["role_archetype"],
      "description": "Pattern description",
      "priority": "P0"
    }
  ],
  "suggested_patches": [
    {
      "level": 1,
      "target": "role_archetype",
      "patch_type": "few-shot example | constraint | chain-of-thought | section rewrite",
      "description": "What to change and why",
      "prompt_text": "The exact text to add or replace in the prompt"
    }
  ],
  "patched_prompt": "The FULL patched system prompt with all suggested Level 1-2 changes applied"
}
```\n""")

    parts.append("**Rules:**")
    parts.append("- Classify EVERY error using the taxonomy")
    parts.append("- Prioritize patterns by frequency (P0=highest freq, P3=lowest)")
    parts.append("- Only suggest Level 1 (few-shot) and Level 2 (constraint) patches")
    parts.append("- The patched_prompt must be the complete prompt, not a diff")
    parts.append("- Keep all existing examples; add new ones only for error patterns")
    parts.append("- Do NOT add more than 2 new examples (diminishing returns)")
    parts.append("- Return ONLY the JSON object, no markdown fences around it")

    return "\n".join(parts)


async def collect_errors(
    store: EvalStore, run_id: int | None
) -> tuple[list[dict], dict[str, int]]:
    """Collect all errors and correct counts from field reviews.

    Returns (errors, correct_summary).
    """
    if run_id:
        run_ids = [run_id]
    else:
        runs = await store.get_runs_with_reviews()
        run_ids = [r["id"] for r in runs]

    if not run_ids:
        return [], {}

    corpus = await store.get_corpus()
    corpus_map = {p["id"]: p for p in corpus}

    errors: list[dict] = []
    correct_counts: dict[str, int] = {}

    for rid in run_ids:
        all_reviews = await store.get_all_field_reviews_for_run(rid)
        results = await store.get_results(rid)
        result_map = {r["id"]: r for r in results}

        for result_id, reviews in all_reviews.items():
            result = result_map.get(result_id)
            if not result:
                continue
            posting = corpus_map.get(result["posting_id"], {})

            for review in reviews:
                if review["is_correct"] == -1:
                    continue  # skip can't-assess

                if review["is_correct"] == 1 and not review.get("correct_value"):
                    # Correct as-is
                    correct_counts[review["field_name"]] = (
                        correct_counts.get(review["field_name"], 0) + 1
                    )
                    continue

                # Error or improvement — include in analysis
                errors.append(
                    {
                        "posting_id": result["posting_id"],
                        "title": posting.get("title", "Unknown"),
                        "full_text": posting.get("full_text", ""),
                        "field_name": review["field_name"],
                        "model_value": review.get("model_value"),
                        "correct_value": review.get("correct_value"),
                        "is_correct": review["is_correct"],
                        "review_type": "improvement"
                        if review["is_correct"] == 1
                        else "error",
                    }
                )

    return errors, correct_counts


async def run_analysis(args: argparse.Namespace) -> None:
    store = EvalStore(args.db)
    await store.init()

    try:
        errors, correct_summary = await collect_errors(store, args.run_id)

        if not errors:
            print("No errors found in field reviews. Nothing to analyze.")
            if correct_summary:
                print(
                    f"\nAll {sum(correct_summary.values())} reviewed fields are correct:"
                )
                for field, count in sorted(
                    correct_summary.items(), key=lambda x: -x[1]
                ):
                    print(f"  {field}: {count}")
            return

        print(
            f"Found {len(errors)} errors across {len(set(e['posting_id'] for e in errors))} postings"
        )
        if correct_summary:
            print(f"  + {sum(correct_summary.values())} correct fields")
        print(f"\nCalling {args.model} for analysis...\n")

        user_message = _build_analysis_prompt(errors, correct_summary, PASS1_PROMPT)

        system = (
            "You are an expert at optimizing LLM prompts for structured data extraction. "
            "You analyze extraction errors, identify patterns, and produce targeted prompt patches. "
            "Respond with a single JSON object."
        )

        response = await call_llm(
            model=args.model,
            system_prompt=system,
            user_message=user_message,
            max_tokens=16384,
        )

        print(
            f"Cost: ${response.cost_usd:.4f} | Tokens: {response.input_tokens}→{response.output_tokens}"
        )
        print(f"Latency: {response.latency_ms}ms\n")

        # Parse and display
        content = response.content.strip()
        # Strip markdown fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3].rstrip()

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            print("Warning: LLM response was not valid JSON. Raw output:\n")
            print(content)
            if args.output:
                Path(args.output).write_text(content)
                print(f"\nRaw output saved to {args.output}")
            return

        # Display classified errors
        print("=" * 60)
        print("CLASSIFIED ERRORS")
        print("=" * 60)
        for err in result.get("classified_errors", []):
            print(
                f"  #{err.get('error_num', '?')} {err.get('field', '?')}: "
                f"{err.get('error_type', '?')}"
            )
            print(f"    → {err.get('explanation', '')}")
            if err.get("root_cause"):
                print(f"    Root cause: {err['root_cause']}")
            print()

        # Display patterns
        patterns = result.get("patterns", [])
        if patterns:
            print("=" * 60)
            print("ERROR PATTERNS")
            print("=" * 60)
            for pat in patterns:
                print(
                    f"  [{pat.get('priority', '?')}] {pat.get('error_type', '?')} "
                    f"(x{pat.get('count', '?')})"
                )
                print(f"    Fields: {', '.join(pat.get('fields_affected', []))}")
                print(f"    {pat.get('description', '')}")
                print()

        # Display patches
        patches = result.get("suggested_patches", [])
        if patches:
            print("=" * 60)
            print("SUGGESTED PATCHES")
            print("=" * 60)
            for patch in patches:
                print(
                    f"  Level {patch.get('level', '?')} — {patch.get('target', '?')} "
                    f"({patch.get('patch_type', '?')})"
                )
                print(f"    {patch.get('description', '')}")
                if patch.get("prompt_text"):
                    preview = patch["prompt_text"][:200]
                    print(
                        f"    Text: {preview}{'...' if len(patch.get('prompt_text', '')) > 200 else ''}"
                    )
                print()

        # Save output
        if args.output:
            Path(args.output).write_text(json.dumps(result, indent=2))
            print(f"Full analysis saved to {args.output}")

        # Save patched prompt
        patched = result.get("patched_prompt")
        if patched:
            patch_path = (
                Path(args.output).with_suffix(".prompt.txt") if args.output else None
            )
            if patch_path:
                patch_path.write_text(patched)
                print(f"Patched prompt saved to {patch_path}")
            else:
                print("\n" + "=" * 60)
                print("PATCHED PROMPT (use --output to save to file)")
                print("=" * 60)
                print(patched[:500] + "..." if len(patched) > 500 else patched)

    finally:
        await store.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze eval errors and suggest prompt improvements."
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        choices=list(MODELS.keys()),
        help=f"Model for analysis (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--run-id", type=int, help="Analyze specific run (default: all reviewed)"
    )
    parser.add_argument("--output", "-o", help="Save JSON analysis to file")
    parser.add_argument("--db", default=DEFAULT_DB, help="Database path")

    args = parser.parse_args()
    asyncio.run(run_analysis(args))


if __name__ == "__main__":
    main()
