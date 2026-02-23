"""Tests for FastAPI API layer."""

import json
import os
import tempfile

import eval.api as api_module
import pytest
from eval.api import app, get_store
from eval.store import EvalStore
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
async def setup_store(tmp_path):
    """Initialize a fresh in-memory store for each test."""
    db_path = str(tmp_path / "test.db")
    store = EvalStore(db_path)
    await store.init()
    api_module._store = store
    yield store
    await store.close()
    api_module._store = None


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_get_runs_empty():
    """GET /api/runs returns empty list when no runs exist."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/runs")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_config_models():
    """GET /api/config/models returns the MODELS dict."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/config/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "haiku-3.5" in data
    assert "deepseek-v3" in data


@pytest.mark.asyncio
async def test_get_config_prompts():
    """GET /api/config/prompts/1 returns pass1 prompt list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/config/prompts/1")
    assert resp.status_code == 200
    data = resp.json()
    assert "pass1_v1" in data


@pytest.mark.asyncio
async def test_get_corpus_empty():
    """GET /api/corpus returns empty list when no corpus loaded."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/corpus")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_comparisons_empty():
    """GET /api/comparisons returns empty list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/comparisons")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_elo_empty():
    """GET /api/elo returns empty dict when no comparisons."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/elo")
    assert resp.status_code == 200
    assert resp.json() == {}


@pytest.mark.asyncio
async def test_get_run_not_found():
    """GET /api/runs/999 returns 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/runs/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_post_comparison():
    """POST /api/comparisons creates a comparison."""
    store = get_store()
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
    run_a = await store.create_run(1, "haiku-3.5", "pass1_v1", 1)
    run_b = await store.create_run(1, "gpt-4o-mini", "pass1_v1", 1)
    await store.insert_result(run_a, "p1", "{}", {}, True, 100, 50, 0.001, 500)
    await store.insert_result(run_b, "p1", "{}", {}, True, 80, 40, 0.0005, 300)

    results_a = await store.get_results(run_a)
    results_b = await store.get_results(run_b)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/comparisons",
            json={
                "posting_id": "p1",
                "result_a_id": results_a[0]["id"],
                "result_b_id": results_b[0]["id"],
                "winner": "a",
                "notes": "A was better",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data


@pytest.mark.asyncio
async def test_post_field_review():
    """POST /api/field-reviews creates a field review."""
    store = get_store()
    await store.insert_corpus(
        [
            {
                "id": "p2",
                "company_slug": "bds",
                "title": "Rep",
                "location": "NY",
                "full_text": "Text",
            }
        ]
    )
    run_id = await store.create_run(1, "haiku-3.5", "pass1_v1", 1)
    result_id = await store.insert_result(
        run_id,
        "p2",
        '{"role_archetype": "field_rep"}',
        {"role_archetype": "field_rep"},
        True,
        100,
        50,
        0.001,
        500,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/field-reviews",
            json={
                "result_id": result_id,
                "field_name": "role_archetype",
                "model_value": "field_rep",
                "is_correct": 1,
                "correct_value": None,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data


@pytest.mark.asyncio
async def test_post_comparison_invalid_winner():
    """POST /api/comparisons rejects invalid winner value."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/comparisons",
            json={
                "posting_id": "p1",
                "result_a_id": 1,
                "result_b_id": 2,
                "winner": "invalid",
            },
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_run_starts_execution():
    """POST /api/runs starts a background run and returns tracking_id."""
    from unittest.mock import AsyncMock, patch

    from eval.providers import LLMResponse

    mock_response = LLMResponse(
        content='{"role_archetype": "field_rep"}',
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
        latency_ms=500,
    )

    corpus_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(
        [
            {
                "id": "test-post-1",
                "company_slug": "bds",
                "title": "Rep",
                "location": "NY",
                "full_text": "Text",
            }
        ],
        corpus_file,
    )
    corpus_file.close()

    try:
        with patch("eval.api.CORPUS_PATH", corpus_file.name):
            with patch("eval.runner.call_llm", new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = mock_response
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post(
                        "/api/runs",
                        json={
                            "pass_number": 1,
                            "model": "haiku-3.5",
                            "prompt_version": "pass1_v1",
                            "concurrency": 1,
                        },
                    )

                assert resp.status_code == 200
                data = resp.json()
                assert "tracking_id" in data
                assert data["status"] == "starting"

                # Wait for the background task to complete within patch context
                # so mock_llm stays active for the entire task lifetime
                import asyncio

                for task in list(api_module._background_tasks):
                    await asyncio.wait_for(task, timeout=5.0)
    finally:
        os.unlink(corpus_file.name)


@pytest.mark.asyncio
async def test_post_run_invalid_model():
    """POST /api/runs rejects unknown model alias."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/runs",
            json={
                "pass_number": 1,
                "model": "nonexistent-model",
                "prompt_version": "pass1_v1",
            },
        )
    assert resp.status_code == 400
