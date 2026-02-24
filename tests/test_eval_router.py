from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from compgraph.api.deps import get_db
from compgraph.main import app


def _make_mock_result(scalars_return=None, all_return=None):
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = all_return or []
    mock_result.scalars.return_value = mock_scalars
    mock_result.all.return_value = all_return or []
    mock_result.scalar_one_or_none.return_value = scalars_return
    return mock_result


def _make_mock_session(scalars_return=None, all_return=None, side_effects=None):
    mock_session = AsyncMock()
    if side_effects is not None:
        mock_session.execute = AsyncMock(side_effect=side_effects)
    else:
        mock_result = _make_mock_result(scalars_return=scalars_return, all_return=all_return)
        mock_session.execute = AsyncMock(return_value=mock_result)
    return mock_session


async def _empty_db_override() -> AsyncGenerator:
    mock_session = _make_mock_session()
    yield mock_session


@pytest.fixture
def mock_empty_db():
    async def _override():
        mock_session = _make_mock_session()
        yield mock_session

    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.clear()


class TestEvalCorpusEndpoint:
    def test_get_corpus_returns_empty_list(self, mock_empty_db) -> None:
        with TestClient(app) as client:
            resp = client.get("/api/eval/corpus")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_corpus_returns_items(self) -> None:
        fake_entry = MagicMock()
        fake_entry.id = "posting_abc"
        fake_entry.company_slug = "marketsource"
        fake_entry.title = "Field Rep"
        fake_entry.location = "Austin, TX"
        fake_entry.full_text = "Full description here"
        fake_entry.reference_pass1 = None
        fake_entry.reference_pass2 = None

        async def _override():
            mock_session = _make_mock_session(all_return=[fake_entry])
            yield mock_session

        app.dependency_overrides[get_db] = _override
        try:
            with TestClient(app) as client:
                resp = client.get("/api/eval/corpus")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["id"] == "posting_abc"
            assert data[0]["company_slug"] == "marketsource"
        finally:
            app.dependency_overrides.clear()


class TestEvalModelsEndpoint:
    def test_get_models_returns_supported_list(self) -> None:
        with TestClient(app) as client:
            resp = client.get("/api/eval/models")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 4
        ids = [m["id"] for m in data]
        assert "claude-haiku-4-5-20251001" in ids
        assert "claude-sonnet-4-5-20251001" in ids
        assert "claude-sonnet-4-6" in ids
        assert "claude-opus-4-6" in ids
        assert all(isinstance(m["id"], str) and isinstance(m["label"], str) for m in data)


class TestEvalRunsEndpoint:
    def test_get_runs_returns_empty_list(self, mock_empty_db) -> None:
        with TestClient(app) as client:
            resp = client.get("/api/eval/runs")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_run_not_found(self, mock_empty_db) -> None:
        run_id = uuid.uuid4()
        with TestClient(app) as client:
            resp = client.get(f"/api/eval/runs/{run_id}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Run not found"

    def test_get_run_found(self) -> None:
        run_id = uuid.uuid4()
        fake_run = MagicMock()
        fake_run.id = run_id
        fake_run.pass_number = 1
        fake_run.model = "claude-haiku-4-5-20251001"
        fake_run.prompt_version = "v1"
        fake_run.corpus_size = 10
        fake_run.total_input_tokens = None
        fake_run.total_output_tokens = None
        fake_run.total_cost_usd = None
        fake_run.total_duration_ms = None
        fake_run.created_at = datetime(2026, 2, 22, tzinfo=UTC)

        async def _override():
            mock_session = _make_mock_session(scalars_return=fake_run)
            yield mock_session

        app.dependency_overrides[get_db] = _override
        try:
            with TestClient(app) as client:
                resp = client.get(f"/api/eval/runs/{run_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == str(run_id)
            assert data["model"] == "claude-haiku-4-5-20251001"
            assert data["pass_number"] == 1
        finally:
            app.dependency_overrides.clear()


class TestEvalLeaderboardEndpoint:
    def test_get_leaderboard_empty(self, mock_empty_db) -> None:
        with (
            patch(
                "compgraph.eval.router._get_field_accuracy_for_run",
                new=AsyncMock(return_value={}),
            ),
            TestClient(app) as client,
        ):
            resp = client.get("/api/eval/leaderboard-data")
        assert resp.status_code == 200
        data = resp.json()
        assert "runs" in data
        assert "elo" in data
        assert "comparisons" in data
        assert "field_accuracy" in data
        assert "results" in data
        assert data["runs"] == []
        assert data["elo"] == {}
        assert data["comparisons"] == []

    def test_get_elo_empty(self, mock_empty_db) -> None:
        with TestClient(app) as client:
            resp = client.get("/api/eval/elo")
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_get_comparisons_empty(self, mock_empty_db) -> None:
        with TestClient(app) as client:
            resp = client.get("/api/eval/comparisons")
        assert resp.status_code == 200
        assert resp.json() == []


class TestEvalRunsPostEndpoint:
    def test_create_run_no_corpus(self, mock_empty_db) -> None:
        with (
            patch("compgraph.eval.router._CORPUS_PATH") as mock_path,
            TestClient(app) as client,
        ):
            mock_path.exists.return_value = False
            resp = client.post(
                "/api/eval/runs",
                json={
                    "pass_number": 1,
                    "model": "claude-haiku-4-5-20251001",
                    "prompt_version": "v1",
                    "concurrency": 5,
                },
            )
        assert resp.status_code == 400
        assert "corpus" in resp.json()["detail"].lower()

    def test_create_run_rejects_unknown_model(self, mock_empty_db) -> None:
        with (
            patch("compgraph.eval.router._CORPUS_PATH") as mock_path,
            TestClient(app) as client,
        ):
            mock_path.exists.return_value = True
            mock_path.read_text.return_value = "[]"
            resp = client.post(
                "/api/eval/runs",
                json={
                    "pass_number": 1,
                    "model": "gpt-4",
                    "prompt_version": "pass1_v1",
                    "concurrency": 5,
                },
            )
        assert resp.status_code == 422
        detail = resp.json().get("detail", [])
        assert isinstance(detail, list)
        msg = detail[0].get("msg", "") if detail else ""
        assert "Unsupported model 'gpt-4'" in msg
