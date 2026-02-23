"""Tests for evaluation runner."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from eval.providers import LLMResponse
from eval.runner import load_corpus, run_evaluation
from eval.store import EvalStore


@pytest_asyncio.fixture
async def store(tmp_path: Path):
    s = EvalStore(str(tmp_path / "test.db"))
    await s.init()
    yield s
    await s.close()


@pytest.fixture
def corpus_file(tmp_path: Path) -> Path:
    """Create a minimal corpus JSON file."""
    postings = [
        {
            "id": "post-1",
            "company_slug": "bds",
            "title": "Field Rep - Samsung",
            "location": "Atlanta, GA",
            "full_text": "Visit Best Buy stores weekly. $18-22/hr. Commission available.",
        },
        {
            "id": "post-2",
            "company_slug": "troc",
            "title": "Merchandiser",
            "location": "Dallas, TX",
            "full_text": "Stock shelves at Target locations. Part-time.",
        },
    ]
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(postings))
    return path


def test_load_corpus(corpus_file: Path):
    """Should load postings from JSON file."""
    postings = load_corpus(str(corpus_file))
    assert len(postings) == 2
    assert postings[0]["id"] == "post-1"


async def test_run_evaluation_stores_results(store: EvalStore, corpus_file: Path):
    """Runner should create a run, call LLM for each posting, store results."""
    mock_response = LLMResponse(
        content='{"role_archetype": "field_rep", "pay_min": 18.0}',
        input_tokens=500,
        output_tokens=100,
        cost_usd=0.002,
        latency_ms=800,
    )

    with patch("eval.runner.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response
        summary = await run_evaluation(
            store=store,
            pass_number=1,
            model="haiku-4.5",
            prompt_version="pass1_v1",
            corpus_path=str(corpus_file),
            concurrency=2,
        )

    assert summary.total == 2
    assert summary.succeeded == 2
    assert summary.failed == 0
    assert mock_llm.call_count == 2

    runs = await store.get_all_runs()
    assert len(runs) == 1
    assert runs[0]["model"] == "haiku-4.5"

    results = await store.get_results(runs[0]["id"])
    assert len(results) == 2
    assert all(r["parse_success"] for r in results)


async def test_run_handles_parse_failure(store: EvalStore, corpus_file: Path):
    """Runner should store parse failures without crashing."""
    mock_response = LLMResponse(
        content="This is not valid JSON at all",
        input_tokens=500,
        output_tokens=100,
        cost_usd=0.002,
        latency_ms=800,
    )

    with patch("eval.runner.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response
        summary = await run_evaluation(
            store=store,
            pass_number=1,
            model="haiku-4.5",
            prompt_version="pass1_v1",
            corpus_path=str(corpus_file),
            concurrency=2,
        )

    assert summary.total == 2
    assert summary.succeeded == 0
    assert summary.failed == 2

    results = await store.get_results(1)
    assert all(not r["parse_success"] for r in results)
    assert all(r["raw_response"] is not None for r in results)
