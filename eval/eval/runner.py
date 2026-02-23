"""Evaluation runner — executes prompt x model combos against a corpus."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

from eval.config import DEFAULT_MAX_TOKENS_PASS1, DEFAULT_MAX_TOKENS_PASS2
from eval.prompts import load_prompt
from eval.providers import call_llm
from eval.schemas import Pass1Result, Pass2Result
from eval.store import EvalStore


@dataclass
class RunSummary:
    """Summary of an evaluation run."""

    run_id: int = 0
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    total_cost_usd: float = 0.0
    total_duration_ms: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0


def load_corpus(corpus_path: str) -> list[dict]:
    """Load corpus postings from a JSON file."""
    return json.loads(Path(corpus_path).read_text())


def strip_markdown_fences(text: str) -> str:
    """Strip markdown code fences from LLM response."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def parse_result(raw: str, pass_number: int) -> dict | None:
    """Parse raw LLM response into validated Pydantic model, return dict or None."""
    try:
        cleaned = strip_markdown_fences(raw)
        data = json.loads(cleaned)
        if pass_number == 1:
            result = Pass1Result(**data)
        else:
            result = Pass2Result(**data)
        return result.model_dump()
    except Exception:
        return None


async def _process_posting(
    posting: dict,
    model: str,
    system_prompt: str,
    build_fn: Callable,
    pass_number: int,
    max_tokens: int,
    store: EvalStore,
    run_id: int,
    semaphore: asyncio.Semaphore,
) -> tuple[bool, int, int, float, int]:
    """Process a single posting. Returns (success, in_tok, out_tok, cost, latency)."""
    async with semaphore:
        build_kwargs = {
            "title": posting["title"],
            "location": posting.get("location", ""),
            "full_text": posting["full_text"],
        }
        if pass_number == 2 and posting.get("content_role_specific"):
            build_kwargs["content_role_specific"] = posting["content_role_specific"]

        user_message = build_fn(**build_kwargs)

        try:
            response = await call_llm(
                model=model,
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=max_tokens,
            )
        except Exception:
            logger.exception("LLM call failed for posting %s", posting["id"])
            await store.insert_result(
                run_id=run_id,
                posting_id=posting["id"],
                raw_response="",
                parsed_result=None,
                parse_success=False,
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                latency_ms=0,
            )
            return (False, 0, 0, 0.0, 0)

        parsed = parse_result(response.content, pass_number)

        await store.insert_result(
            run_id=run_id,
            posting_id=posting["id"],
            raw_response=response.content,
            parsed_result=parsed,
            parse_success=parsed is not None,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
        )

        return (
            parsed is not None,
            response.input_tokens,
            response.output_tokens,
            response.cost_usd,
            response.latency_ms,
        )


async def run_evaluation(
    store: EvalStore,
    pass_number: int,
    model: str,
    prompt_version: str,
    corpus_path: str,
    concurrency: int = 5,
    on_progress: Callable | None = None,
) -> RunSummary:
    """Run an evaluation: load corpus, call LLM for each posting, store results.

    Args:
        store: EvalStore instance
        pass_number: 1 or 2
        model: Model alias from config.MODELS
        prompt_version: Prompt module name (e.g. "pass1_v1")
        corpus_path: Path to corpus.json
        concurrency: Max parallel LLM calls
        on_progress: Optional callback(completed, total) for UI progress
    """
    postings = load_corpus(corpus_path)
    system_prompt, build_fn = load_prompt(prompt_version)
    max_tokens = DEFAULT_MAX_TOKENS_PASS1 if pass_number == 1 else DEFAULT_MAX_TOKENS_PASS2

    await store.insert_corpus(postings)

    run_id = await store.create_run(pass_number, model, prompt_version, len(postings))

    semaphore = asyncio.Semaphore(concurrency)
    summary = RunSummary(run_id=run_id, total=len(postings))

    start = time.perf_counter()

    tasks = [
        _process_posting(
            posting,
            model,
            system_prompt,
            build_fn,
            pass_number,
            max_tokens,
            store,
            run_id,
            semaphore,
        )
        for posting in postings
    ]

    for coro in asyncio.as_completed(tasks):
        success, in_tok, out_tok, cost, latency = await coro
        if success:
            summary.succeeded += 1
        else:
            summary.failed += 1
        summary.total_input_tokens += in_tok
        summary.total_output_tokens += out_tok
        summary.total_cost_usd += cost
        if on_progress:
            on_progress(summary.succeeded + summary.failed, summary.total)

    summary.total_duration_ms = int((time.perf_counter() - start) * 1000)

    await store.update_run_totals(
        run_id,
        summary.total_input_tokens,
        summary.total_output_tokens,
        summary.total_cost_usd,
        summary.total_duration_ms,
    )

    return summary
