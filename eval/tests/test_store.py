"""Tests for SQLite store."""

from pathlib import Path

import pytest_asyncio
from eval.store import EvalStore


@pytest_asyncio.fixture
async def store(tmp_path: Path):
    """Create a temporary store for testing."""
    db_path = tmp_path / "test.db"
    s = EvalStore(str(db_path))
    await s.init()
    yield s
    await s.close()


async def test_init_creates_tables(store: EvalStore):
    """init() should create all 4 tables."""
    tables = await store.list_tables()
    assert "corpus" in tables
    assert "runs" in tables
    assert "results" in tables
    assert "comparisons" in tables


async def test_insert_and_get_corpus(store: EvalStore):
    """Should insert and retrieve corpus postings."""
    posting = {
        "id": "abc-123",
        "company_slug": "bds",
        "title": "Field Rep",
        "location": "Atlanta, GA",
        "full_text": "Full job description here.",
    }
    await store.insert_corpus([posting])
    results = await store.get_corpus()
    assert len(results) == 1
    assert results[0]["id"] == "abc-123"
    assert results[0]["title"] == "Field Rep"


async def test_create_and_get_run(store: EvalStore):
    """Should create a run and retrieve it."""
    run_id = await store.create_run(
        pass_number=1,
        model="haiku-4.5",
        prompt_version="pass1_v1",
        corpus_size=10,
    )
    assert run_id > 0
    run = await store.get_run(run_id)
    assert run["model"] == "haiku-4.5"
    assert run["corpus_size"] == 10


async def test_insert_and_get_result(store: EvalStore):
    """Should insert a result and retrieve it by run."""
    await store.insert_corpus(
        [
            {
                "id": "post-1",
                "company_slug": "bds",
                "title": "Rep",
                "location": "NY",
                "full_text": "Text",
            }
        ]
    )
    run_id = await store.create_run(1, "haiku-4.5", "pass1_v1", 1)
    await store.insert_result(
        run_id=run_id,
        posting_id="post-1",
        raw_response='{"role_archetype": "field_rep"}',
        parsed_result={"role_archetype": "field_rep"},
        parse_success=True,
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
        latency_ms=500,
    )
    results = await store.get_results(run_id)
    assert len(results) == 1
    assert results[0]["parse_success"] == 1
    assert results[0]["posting_id"] == "post-1"


async def test_insert_comparison(store: EvalStore):
    """Should insert a comparison and retrieve comparisons for a run pair."""
    await store.insert_corpus(
        [
            {
                "id": "p1",
                "company_slug": "bds",
                "title": "Rep",
                "location": "NY",
                "full_text": "Text",
            }
        ]
    )
    run_a = await store.create_run(1, "haiku-4.5", "v1", 1)
    run_b = await store.create_run(1, "gpt-4o-mini", "v1", 1)
    await store.insert_result(run_a, "p1", "{}", {}, True, 100, 50, 0.001, 500)
    await store.insert_result(run_b, "p1", "{}", {}, True, 80, 40, 0.0005, 300)

    results_a = await store.get_results(run_a)
    results_b = await store.get_results(run_b)

    await store.insert_comparison(
        posting_id="p1",
        result_a_id=results_a[0]["id"],
        result_b_id=results_b[0]["id"],
        winner="a",
        notes="A extracted pay correctly",
    )
    comps = await store.get_comparisons()
    assert len(comps) == 1
    assert comps[0]["winner"] == "a"


async def test_update_run_totals(store: EvalStore):
    """Should update run totals after results are collected."""
    run_id = await store.create_run(1, "haiku-4.5", "v1", 10)
    await store.update_run_totals(
        run_id,
        total_input_tokens=5000,
        total_output_tokens=2000,
        total_cost_usd=0.05,
        total_duration_ms=30000,
    )
    run = await store.get_run(run_id)
    assert run["total_input_tokens"] == 5000
    assert run["total_cost_usd"] == 0.05
