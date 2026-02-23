"""End-to-end smoke test: corpus -> run -> compare -> elo."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest_asyncio
from eval.elo import calculate_elo_ratings
from eval.providers import LLMResponse
from eval.runner import run_evaluation
from eval.store import EvalStore


@pytest_asyncio.fixture
async def store(tmp_path: Path):
    s = EvalStore(str(tmp_path / "test.db"))
    await s.init()
    yield s
    await s.close()


def _corpus_file(tmp_path: Path) -> Path:
    postings = [
        {
            "id": "p1",
            "company_slug": "bds",
            "title": "Field Rep",
            "location": "Atlanta",
            "full_text": "Visit stores. $18/hr.",
        },
        {
            "id": "p2",
            "company_slug": "troc",
            "title": "Merchandiser",
            "location": "Dallas",
            "full_text": "Stock shelves at Target.",
        },
    ]
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(postings))
    return path


async def test_full_flow(store: EvalStore, tmp_path: Path):
    """Run two evaluations, add comparisons, compute Elo."""
    corpus_file = _corpus_file(tmp_path)

    good_response = LLMResponse(
        content='{"role_archetype": "field_rep", "pay_min": 18.0, "pay_max": 18.0}',
        input_tokens=500,
        output_tokens=100,
        cost_usd=0.002,
        latency_ms=800,
    )
    weak_response = LLMResponse(
        content='{"role_archetype": "field_rep"}',
        input_tokens=400,
        output_tokens=80,
        cost_usd=0.001,
        latency_ms=600,
    )

    # Run A: "good" model
    with patch("eval.runner.call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = good_response
        summary_a = await run_evaluation(store, 1, "haiku-4.5", "pass1_v1", str(corpus_file))
    assert summary_a.succeeded == 2

    # Run B: "weak" model
    with patch("eval.runner.call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = weak_response
        summary_b = await run_evaluation(store, 1, "gpt-4o-mini", "pass1_v1", str(corpus_file))
    assert summary_b.succeeded == 2

    # Get results for comparisons
    results_a = await store.get_results(summary_a.run_id)
    results_b = await store.get_results(summary_b.run_id)

    # Add comparisons: A wins both
    for ra, rb in zip(results_a, results_b):
        await store.insert_comparison(ra["posting_id"], ra["id"], rb["id"], "a")

    # Compute Elo
    comparisons = await store.get_comparisons()
    run_map = {}
    for r in results_a:
        run_map[r["id"]] = "haiku-4.5/pass1_v1"
    for r in results_b:
        run_map[r["id"]] = "gpt-4o-mini/pass1_v1"

    ratings = calculate_elo_ratings(comparisons, run_map)
    assert ratings["haiku-4.5/pass1_v1"] > ratings["gpt-4o-mini/pass1_v1"]
    assert ratings["haiku-4.5/pass1_v1"] > 1500
