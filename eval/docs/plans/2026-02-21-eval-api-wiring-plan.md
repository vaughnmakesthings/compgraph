# Eval API Wiring — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a FastAPI HTTP layer on top of the existing Python eval backend, then wire all Next.js frontend pages to consume live data via API calls instead of hardcoded mock arrays.

**Architecture:** `eval/api.py` (new FastAPI app, port 8001) wraps existing modules (store, runner, elo, ground_truth, prompts, config). Next.js proxies `/api/*` to `:8001` in dev. `web/src/lib/api-client.ts` (new) is the single fetch wrapper consumed by all pages.

**Tech Stack:** FastAPI + uvicorn (Python API), Next.js 16 + React 19 (frontend), SQLite via aiosqlite (existing), LiteLLM (existing)

**Design doc:** `docs/plans/2026-02-21-eval-api-wiring-design.md`

---

## Task 1: Add FastAPI + uvicorn Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add dependencies**

Add `fastapi` and `uvicorn[standard]` to the project dependencies in `pyproject.toml`:

```toml
dependencies = [
    "litellm>=1.50",
    "streamlit>=1.40",
    "aiosqlite>=0.20",
    "pydantic>=2.0",
    "python-dotenv>=1.0",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
]
```

**Step 2: Install**

```bash
cd /Users/vmud/Documents/dev/projects/compgraph-eval-issue-14
uv sync
```

Expected: deps install successfully, no errors.

**Step 3: Verify existing tests still pass**

```bash
uv run pytest -q
```

Expected: 78 passed

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add fastapi + uvicorn dependencies"
```

---

## Task 2: FastAPI App — Read-Only Endpoints

**Files:**
- Create: `eval/api.py`
- Test: `tests/test_api.py`

This task builds the core API app with all GET endpoints. POST endpoints come in Tasks 3-4.

**Step 1: Write the failing test**

```python
# tests/test_api.py
"""Tests for FastAPI API layer."""

import json
import pytest
from httpx import ASGITransport, AsyncClient

from eval.api import app


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
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_api.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'eval.api'`

**Step 3: Write eval/api.py with read-only endpoints**

```python
# eval/api.py
"""FastAPI HTTP layer for the evaluation backend.

Thin wrapper over existing modules — no business logic here.

Usage:
    uvicorn eval.api:app --port 8001 --reload
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from eval.config import MODELS
from eval.elo import calculate_elo_ratings
from eval.prompts import list_prompts
from eval.store import EvalStore

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = str(DATA_DIR / "eval.db")
CORPUS_PATH = str(DATA_DIR / "corpus.json")

# Module-level store — initialized in lifespan
_store: EvalStore | None = None

# In-memory progress tracking for running evaluations
_run_progress: dict[int, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _store
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _store = EvalStore(os.environ.get("EVAL_DB_PATH", DB_PATH))
    await _store.init()
    yield
    await _store.close()


app = FastAPI(title="CompGraph Eval API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_store() -> EvalStore:
    assert _store is not None, "Store not initialized"
    return _store


# --- Config ---


@app.get("/api/config/models")
async def get_models():
    return MODELS


@app.get("/api/config/prompts/{pass_number}")
async def get_prompts(pass_number: int):
    return list_prompts(pass_number)


# --- Runs ---


@app.get("/api/runs")
async def get_runs():
    store = get_store()
    return await store.get_all_runs()


@app.get("/api/runs/{run_id}")
async def get_run(run_id: int):
    store = get_store()
    run = await store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.delete("/api/runs/{run_id}")
async def delete_run(run_id: int):
    store = get_store()
    run = await store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    await store.delete_run(run_id)
    return {"status": "deleted"}


@app.get("/api/runs/{run_id}/results")
async def get_run_results(run_id: int):
    store = get_store()
    run = await store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return await store.get_results(run_id)


@app.get("/api/runs/{run_id}/field-accuracy")
async def get_run_field_accuracy(run_id: int):
    store = get_store()
    run = await store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return await store.get_field_accuracy(run_id)


@app.get("/api/runs/{run_id}/field-reviews")
async def get_run_field_reviews(run_id: int):
    store = get_store()
    run = await store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    reviews = await store.get_all_field_reviews_for_run(run_id)
    # Convert int keys to strings for JSON serialization
    return {str(k): v for k, v in reviews.items()}


@app.get("/api/runs/{run_id}/progress")
async def get_run_progress(run_id: int):
    if run_id in _run_progress:
        return _run_progress[run_id]
    store = get_store()
    run = await store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"status": "completed", "completed": run["corpus_size"], "total": run["corpus_size"]}


# --- Corpus ---


@app.get("/api/corpus")
async def get_corpus():
    store = get_store()
    return await store.get_corpus()


# --- Comparisons ---


@app.get("/api/comparisons")
async def get_comparisons():
    store = get_store()
    return await store.get_comparisons()


# --- Elo ---


@app.get("/api/elo")
async def get_elo():
    store = get_store()
    runs = await store.get_all_runs()
    comparisons = await store.get_comparisons()
    if not comparisons:
        return {}

    # Build run_map: result_id → "model/prompt_version"
    run_map: dict[int, str] = {}
    for run in runs:
        label = f"{run['model']}/{run['prompt_version']}"
        results = await store.get_results(run["id"])
        for r in results:
            run_map[r["id"]] = label

    return calculate_elo_ratings(comparisons, run_map)
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_api.py -v
```

Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add eval/api.py tests/test_api.py
git commit -m "feat: add FastAPI app with read-only endpoints"
```

---

## Task 3: POST Endpoints — Comparisons + Field Reviews

**Files:**
- Modify: `eval/api.py`
- Modify: `tests/test_api.py`

**Step 1: Write the failing tests**

Add to `tests/test_api.py`:

```python
@pytest.mark.asyncio
async def test_post_comparison():
    """POST /api/comparisons creates a comparison."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First need corpus + 2 runs + results
        # Use the store directly to set up test data
        store = get_store()
        await store.insert_corpus([{
            "id": "p1", "company_slug": "bds",
            "title": "Rep", "location": "NY", "full_text": "Text",
        }])
        run_a = await store.create_run(1, "haiku-3.5", "pass1_v1", 1)
        run_b = await store.create_run(1, "gpt-4o-mini", "pass1_v1", 1)
        await store.insert_result(run_a, "p1", "{}", {}, True, 100, 50, 0.001, 500)
        await store.insert_result(run_b, "p1", "{}", {}, True, 80, 40, 0.0005, 300)

        results_a = await store.get_results(run_a)
        results_b = await store.get_results(run_b)

        resp = await client.post("/api/comparisons", json={
            "posting_id": "p1",
            "result_a_id": results_a[0]["id"],
            "result_b_id": results_b[0]["id"],
            "winner": "a",
            "notes": "A was better",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data


@pytest.mark.asyncio
async def test_post_field_review():
    """POST /api/field-reviews creates a field review."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        store = get_store()
        await store.insert_corpus([{
            "id": "p2", "company_slug": "bds",
            "title": "Rep", "location": "NY", "full_text": "Text",
        }])
        run_id = await store.create_run(1, "haiku-3.5", "pass1_v1", 1)
        result_id = await store.insert_result(
            run_id, "p2", '{"role_archetype": "field_rep"}',
            {"role_archetype": "field_rep"}, True, 100, 50, 0.001, 500
        )

        resp = await client.post("/api/field-reviews", json={
            "result_id": result_id,
            "field_name": "role_archetype",
            "model_value": "field_rep",
            "is_correct": 1,
            "correct_value": None,
        })

    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data


@pytest.mark.asyncio
async def test_post_comparison_invalid_winner():
    """POST /api/comparisons rejects invalid winner value."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/comparisons", json={
            "posting_id": "p1",
            "result_a_id": 1,
            "result_b_id": 2,
            "winner": "invalid",
        })
    assert resp.status_code == 422
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_api.py::test_post_comparison -v
```

Expected: FAIL — no POST endpoint defined

**Step 3: Add POST endpoints to eval/api.py**

Add these Pydantic request models and endpoints to `eval/api.py`:

```python
from pydantic import BaseModel, field_validator


class ComparisonCreate(BaseModel):
    posting_id: str
    result_a_id: int
    result_b_id: int
    winner: str
    notes: str | None = None

    @field_validator("winner")
    @classmethod
    def validate_winner(cls, v: str) -> str:
        if v not in ("a", "b", "tie", "both_bad"):
            raise ValueError("winner must be one of: a, b, tie, both_bad")
        return v


class FieldReviewCreate(BaseModel):
    result_id: int
    field_name: str
    model_value: str | None
    is_correct: int
    correct_value: str | None = None


@app.post("/api/comparisons")
async def create_comparison(body: ComparisonCreate):
    store = get_store()
    comp_id = await store.insert_comparison(
        posting_id=body.posting_id,
        result_a_id=body.result_a_id,
        result_b_id=body.result_b_id,
        winner=body.winner,
        notes=body.notes,
    )
    return {"id": comp_id}


@app.post("/api/field-reviews")
async def create_field_review(body: FieldReviewCreate):
    store = get_store()
    review_id = await store.upsert_field_review(
        result_id=body.result_id,
        field_name=body.field_name,
        model_value=body.model_value,
        is_correct=body.is_correct,
        correct_value=body.correct_value,
    )
    return {"id": review_id}
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_api.py -v
```

Expected: All 10 tests PASS

**Step 5: Commit**

```bash
git add eval/api.py tests/test_api.py
git commit -m "feat: add POST endpoints for comparisons and field reviews"
```

---

## Task 4: POST /api/runs — Background Run Execution

**Files:**
- Modify: `eval/api.py`
- Modify: `tests/test_api.py`

This is the trickiest endpoint — it spawns a background task and returns immediately.

**Step 1: Write the failing test**

Add to `tests/test_api.py`:

```python
from unittest.mock import AsyncMock, patch
from eval.providers import LLMResponse


@pytest.mark.asyncio
async def test_post_run_starts_execution():
    """POST /api/runs starts a background run and returns run_id."""
    mock_response = LLMResponse(
        content='{"role_archetype": "field_rep"}',
        input_tokens=100, output_tokens=50, cost_usd=0.001, latency_ms=500,
    )

    # Create a minimal corpus file
    import tempfile, json
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump([{
            "id": "test-post-1", "company_slug": "bds",
            "title": "Rep", "location": "NY", "full_text": "Text",
        }], f)
        corpus_path = f.name

    with patch("eval.api.CORPUS_PATH", corpus_path):
        with patch("eval.runner.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/runs", json={
                    "pass_number": 1,
                    "model": "haiku-3.5",
                    "prompt_version": "pass1_v1",
                    "concurrency": 1,
                })

    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert data["status"] == "running"

    import os
    os.unlink(corpus_path)


@pytest.mark.asyncio
async def test_post_run_invalid_model():
    """POST /api/runs rejects unknown model alias."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/runs", json={
            "pass_number": 1,
            "model": "nonexistent-model",
            "prompt_version": "pass1_v1",
        })
    assert resp.status_code == 400
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_api.py::test_post_run_starts_execution -v
```

Expected: FAIL

**Step 3: Add run execution endpoint to eval/api.py**

```python
from eval.config import MODELS
from eval.runner import run_evaluation


class RunCreate(BaseModel):
    pass_number: int
    model: str
    prompt_version: str
    concurrency: int = 5


@app.post("/api/runs")
async def create_run(body: RunCreate):
    if body.model not in MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown model: {body.model}")

    corpus_path = os.environ.get("EVAL_CORPUS_PATH", CORPUS_PATH)
    if not Path(corpus_path).exists():
        raise HTTPException(status_code=400, detail="No corpus file found. Run export_corpus.py first.")

    store = get_store()

    # Start the run synchronously to get the run_id, then hand off to background
    # We need a temporary run_id for progress tracking, so we peek at what
    # run_evaluation will create by pre-creating the run
    from eval.runner import load_corpus
    postings = load_corpus(corpus_path)
    run_id = await store.create_run(
        body.pass_number, body.model, body.prompt_version, len(postings)
    )

    _run_progress[run_id] = {
        "status": "running",
        "completed": 0,
        "total": len(postings),
    }

    async def _execute():
        try:
            def on_progress(completed: int, total: int):
                _run_progress[run_id] = {
                    "status": "running",
                    "completed": completed,
                    "total": total,
                }

            summary = await run_evaluation(
                store=store,
                pass_number=body.pass_number,
                model=body.model,
                prompt_version=body.prompt_version,
                corpus_path=corpus_path,
                concurrency=body.concurrency,
                on_progress=on_progress,
            )
            _run_progress[run_id] = {
                "status": "completed",
                "completed": summary.total,
                "total": summary.total,
                "succeeded": summary.succeeded,
                "failed": summary.failed,
                "cost_usd": summary.total_cost_usd,
                "duration_ms": summary.total_duration_ms,
            }
        except Exception as e:
            _run_progress[run_id] = {
                "status": "failed",
                "error": str(e),
            }

    asyncio.create_task(_execute())
    return {"run_id": run_id, "status": "running", "total": len(postings)}
```

**Note:** The `run_evaluation` function calls `store.create_run` internally, but we already created it above. This will cause a duplicate. We need to refactor slightly — either skip the pre-creation and parse the run_id from the background task result, or modify `run_evaluation` to accept an existing `run_id`. The simpler approach: delete the pre-created run and let `run_evaluation` handle it. But that's fragile. Better: modify the endpoint to not pre-create, and instead have the background task set progress once it has the run_id.

Actually the cleanest approach: create the run first, then have the background task call a modified version that skips `create_run`. But that requires changing `runner.py`. Instead, let's just delete our pre-created run before handing off, and read back the run_id from the result. **Simplest fix:** remove the pre-create, start the background task, and have it set the run_id in progress once known.

Revised endpoint:

```python
@app.post("/api/runs")
async def create_run(body: RunCreate):
    if body.model not in MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown model: {body.model}")

    corpus_path = os.environ.get("EVAL_CORPUS_PATH", CORPUS_PATH)
    if not Path(corpus_path).exists():
        raise HTTPException(status_code=400, detail="No corpus file found")

    store = get_store()
    from eval.runner import load_corpus
    postings = load_corpus(corpus_path)

    # Use a temporary tracking key until we have the real run_id
    import time
    tracking_key = int(time.time() * 1000)
    _run_progress[tracking_key] = {
        "status": "starting",
        "completed": 0,
        "total": len(postings),
    }

    async def _execute():
        try:
            def on_progress(completed: int, total: int):
                _run_progress[tracking_key]["completed"] = completed
                _run_progress[tracking_key]["status"] = "running"

            summary = await run_evaluation(
                store=store,
                pass_number=body.pass_number,
                model=body.model,
                prompt_version=body.prompt_version,
                corpus_path=corpus_path,
                concurrency=body.concurrency,
                on_progress=on_progress,
            )
            _run_progress[tracking_key] = {
                "status": "completed",
                "run_id": summary.run_id,
                "completed": summary.total,
                "total": summary.total,
                "succeeded": summary.succeeded,
                "failed": summary.failed,
                "cost_usd": summary.total_cost_usd,
                "duration_ms": summary.total_duration_ms,
            }
            # Also store under the real run_id for later lookups
            _run_progress[summary.run_id] = _run_progress[tracking_key]
        except Exception as e:
            _run_progress[tracking_key] = {"status": "failed", "error": str(e)}

    asyncio.create_task(_execute())
    return {"tracking_id": tracking_key, "status": "starting", "total": len(postings)}
```

And update the progress endpoint to accept both run_id and tracking_id:

```python
@app.get("/api/progress/{tracking_id}")
async def get_progress(tracking_id: int):
    if tracking_id in _run_progress:
        return _run_progress[tracking_id]
    raise HTTPException(status_code=404, detail="No progress found for this ID")
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_api.py -v
```

Expected: All 12 tests PASS

**Step 5: Commit**

```bash
git add eval/api.py tests/test_api.py
git commit -m "feat: add POST /api/runs with background execution and progress tracking"
```

---

## Task 5: Next.js Proxy Config + API Client

**Files:**
- Modify: `web/next.config.ts`
- Create: `web/src/lib/api-client.ts`
- Test: `web/src/lib/__tests__/api-client.test.ts`

**Step 1: Add proxy rewrites to next.config.ts**

```typescript
// web/next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
```

**Step 2: Write api-client.ts**

```typescript
// web/src/lib/api-client.ts
/**
 * Typed API client for the Python eval backend.
 * All pages consume data through this module.
 */

const API_BASE = "/api";

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`API ${resp.status}: ${text}`);
  }
  return resp.json();
}

// --- Types (matching Python backend responses) ---

export interface Run {
  id: number;
  created_at: string;
  pass_number: number;
  model: string;
  prompt_version: string;
  corpus_size: number;
  total_input_tokens: number | null;
  total_output_tokens: number | null;
  total_cost_usd: number | null;
  total_duration_ms: number | null;
}

export interface Result {
  id: number;
  run_id: number;
  posting_id: string;
  raw_response: string | null;
  parsed_result: string | null; // JSON string
  parse_success: boolean;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms: number;
}

export interface CorpusPosting {
  id: string;
  company_slug: string;
  title: string;
  location: string | null;
  full_text: string;
  reference_pass1: string | null; // JSON string
  reference_pass2: string | null; // JSON string
}

export interface Comparison {
  id: number;
  created_at: string;
  posting_id: string;
  result_a_id: number;
  result_b_id: number;
  winner: "a" | "b" | "tie" | "both_bad";
  notes: string | null;
}

export interface FieldReview {
  id: number;
  created_at: string;
  result_id: number;
  field_name: string;
  model_value: string | null;
  is_correct: number; // 1=correct, 0=wrong, -1=cant-assess
  correct_value: string | null;
}

export interface RunProgress {
  status: "starting" | "running" | "completed" | "failed";
  completed: number;
  total: number;
  run_id?: number;
  succeeded?: number;
  failed?: number;
  cost_usd?: number;
  duration_ms?: number;
  error?: string;
}

// --- Config ---

export async function getModels(): Promise<Record<string, string>> {
  return fetchJSON("/config/models");
}

export async function getPrompts(passNumber: number): Promise<string[]> {
  return fetchJSON(`/config/prompts/${passNumber}`);
}

// --- Runs ---

export async function getRuns(): Promise<Run[]> {
  return fetchJSON("/runs");
}

export async function getRun(id: number): Promise<Run> {
  return fetchJSON(`/runs/${id}`);
}

export async function deleteRun(id: number): Promise<void> {
  await fetchJSON(`/runs/${id}`, { method: "DELETE" });
}

export async function createRun(params: {
  pass_number: number;
  model: string;
  prompt_version: string;
  concurrency?: number;
}): Promise<{ tracking_id: number; status: string; total: number }> {
  return fetchJSON("/runs", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function getRunResults(id: number): Promise<Result[]> {
  return fetchJSON(`/runs/${id}/results`);
}

export async function getRunFieldAccuracy(
  id: number,
): Promise<Record<string, number>> {
  return fetchJSON(`/runs/${id}/field-accuracy`);
}

export async function getRunFieldReviews(
  id: number,
): Promise<Record<string, FieldReview[]>> {
  return fetchJSON(`/runs/${id}/field-reviews`);
}

// --- Progress ---

export async function getProgress(trackingId: number): Promise<RunProgress> {
  return fetchJSON(`/progress/${trackingId}`);
}

// --- Corpus ---

export async function getCorpus(): Promise<CorpusPosting[]> {
  return fetchJSON("/corpus");
}

// --- Comparisons ---

export async function getComparisons(): Promise<Comparison[]> {
  return fetchJSON("/comparisons");
}

export async function createComparison(params: {
  posting_id: string;
  result_a_id: number;
  result_b_id: number;
  winner: "a" | "b" | "tie" | "both_bad";
  notes?: string;
}): Promise<{ id: number }> {
  return fetchJSON("/comparisons", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

// --- Field Reviews ---

export async function createFieldReview(params: {
  result_id: number;
  field_name: string;
  model_value: string | null;
  is_correct: number;
  correct_value?: string | null;
}): Promise<{ id: number }> {
  return fetchJSON("/field-reviews", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

// --- Elo ---

export async function getEloRatings(): Promise<Record<string, number>> {
  return fetchJSON("/elo");
}
```

**Step 3: Write basic test for api-client**

```typescript
// web/src/lib/__tests__/api-client.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { getRuns, getModels, createComparison } from "../api-client";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  mockFetch.mockReset();
});

describe("api-client", () => {
  it("getRuns fetches from /api/runs", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: 1, model: "haiku-3.5" }],
    });
    const runs = await getRuns();
    expect(runs).toHaveLength(1);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/runs",
      expect.objectContaining({ headers: expect.any(Object) }),
    );
  });

  it("getModels fetches from /api/config/models", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ "haiku-3.5": "openrouter/..." }),
    });
    const models = await getModels();
    expect(models).toHaveProperty("haiku-3.5");
  });

  it("createComparison POSTs to /api/comparisons", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 42 }),
    });
    const result = await createComparison({
      posting_id: "p1",
      result_a_id: 1,
      result_b_id: 2,
      winner: "a",
    });
    expect(result.id).toBe(42);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/comparisons",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      text: async () => "Not found",
    });
    await expect(getRuns()).rejects.toThrow("API 404");
  });
});
```

**Step 4: Run frontend tests**

```bash
cd web && npx vitest run src/lib/__tests__/api-client.test.ts
```

Expected: 4 tests PASS

**Step 5: Commit**

```bash
git add web/next.config.ts web/src/lib/api-client.ts web/src/lib/__tests__/api-client.test.ts
git commit -m "feat: add Next.js proxy config and typed API client"
```

---

## Task 6: Wire Run Tests Page

**Files:**
- Modify: `web/src/app/runs/page.tsx`

**Step 1: Rewrite runs page to use API client**

Replace the entire page with a client component that:
- Fetches runs from `getRuns()` on mount
- Fetches models and prompts from config endpoints for the "New Run" form
- "New Run" button opens a form, submits via `createRun()`, polls progress via `getProgress()`
- Table shows real data from API

The page should keep the same visual design (DataTable, StatusBadge, same columns) but swap mock data for API calls. Use `React.useState` + `React.useEffect` for data fetching (no need for SWR/React Query in this phase).

Add a `"use client"` directive since this page needs interactivity.

**Step 2: Verify it renders with the dev server running**

```bash
# Terminal 1: Python API
cd /Users/vmud/Documents/dev/projects/compgraph-eval-issue-14 && uv run uvicorn eval.api:app --port 8001 --reload

# Terminal 2: Next.js
cd /Users/vmud/Documents/dev/projects/compgraph-eval-issue-14/web && npm run dev
```

Navigate to `http://localhost:3000/runs` — should show empty state (no runs in fresh DB).

**Step 3: Commit**

```bash
git add web/src/app/runs/page.tsx
git commit -m "feat: wire Run Tests page to live API"
```

---

## Task 7: Wire Review Page

**Files:**
- Modify: `web/src/app/review/page.tsx`

**Step 1: Rewrite review page**

Client component that:
- Fetches available runs from `getRuns()` for two dropdown selectors
- Loads results for both selected runs via `getRunResults()`
- Loads corpus postings via `getCorpus()`
- Finds common posting IDs between both runs
- Randomizes A/B assignment per posting (client-side, using `Math.random()` seeded per session)
- Renders side-by-side field comparison with diff highlighting (fields that disagree get a warning marker)
- Vote buttons (A/B/Tie/Both bad) POST to `createComparison()` then advance to next posting
- Notes text input included in comparison
- Prev/next navigation with progress counter

Keep the same card layout and Tremor-style design from the current page.

**Step 2: Verify in browser**

Navigate to `http://localhost:3000/review` with both servers running. With runs in the DB, should show comparison UI.

**Step 3: Commit**

```bash
git add web/src/app/review/page.tsx
git commit -m "feat: wire Review page with voting and navigation"
```

---

## Task 8: Wire Accuracy Review Page

**Files:**
- Modify: `web/src/app/accuracy/page.tsx`

**Step 1: Rewrite accuracy page**

Client component that:
- Fetches available runs from `getRuns()` for a run selector dropdown
- Loads results for selected run via `getRunResults()`
- Loads corpus via `getCorpus()`
- Loads existing field reviews via `getRunFieldReviews()`
- Navigates through postings with prev/next buttons
- For each posting: shows posting text, then for each reviewable field (from `ground_truth.REVIEWABLE_FIELDS` — hardcode the list client-side):
  - Shows the extracted value from the model
  - Shows ground truth if available (from `reference_pass1` in corpus)
  - Judgment buttons: Correct (1) / Wrong (0) / Can't Assess (-1)
  - If Wrong: shows text input for correct value
  - Buttons POST to `createFieldReview()`
  - Pre-fills from existing reviews
- Progress bar showing reviewed/total postings

**Step 2: Verify in browser**

Navigate to `http://localhost:3000/accuracy` with runs in the DB. Should show posting + field review UI.

**Step 3: Commit**

```bash
git add web/src/app/accuracy/page.tsx
git commit -m "feat: wire Accuracy Review page with field judgments"
```

---

## Task 9: Wire Leaderboard Page

**Files:**
- Modify: `web/src/app/leaderboard/page.tsx`

**Step 1: Rewrite leaderboard page**

Client component that:
- Fetches runs from `getRuns()`
- Fetches Elo ratings from `getEloRatings()`
- Fetches comparisons from `getComparisons()` to compute win rates
- Fetches field accuracy per run from `getRunFieldAccuracy()`
- Pass filter (Pass 1 / Pass 2) — client-side filter on the runs list
- Elo table: rank, model/prompt, Elo, win%, parse rate, cost, latency
- Field population rate table: per-field accuracy from reviews

Keep DataTable component and existing visual design.

**Step 2: Verify in browser**

Navigate to `http://localhost:3000/leaderboard`. With comparisons in DB, should show computed Elo rankings.

**Step 3: Commit**

```bash
git add web/src/app/leaderboard/page.tsx
git commit -m "feat: wire Leaderboard page with live Elo and field accuracy"
```

---

## Task 10: Wire Prompt Diff Page

**Files:**
- Modify: `web/src/app/prompt-diff/page.tsx`

**Step 1: Rewrite prompt diff page**

Client component that:
- Fetches runs from `getRuns()` for baseline/candidate selector dropdowns
- When both runs selected: loads results for both via `getRunResults()`
- Computes field-level diff client-side:
  - For each common posting: compare parsed fields between runs
  - Count matches, divergences, regressions per field
- Shows summary metrics: baseline accuracy, candidate accuracy, delta
- Shows field-level comparison table with match/diverge indicators

**Step 2: Verify in browser**

Navigate to `http://localhost:3000/prompt-diff` with runs in DB.

**Step 3: Commit**

```bash
git add web/src/app/prompt-diff/page.tsx
git commit -m "feat: wire Prompt Diff page with live run comparison"
```

---

## Task 11: Wire Dashboard Page

**Files:**
- Modify: `web/src/app/page.tsx`

**Step 1: Update dashboard to use API**

The dashboard already computes metrics from mock data. Change it to:
- Fetch runs from `getRuns()` on mount
- Compute KPIs (total runs, avg cost, avg latency) from real data
- Recent Runs table from real data
- Review progress: fetch field review counts from API
- Cost per run: computed from runs data

Keep Tremor components (ProgressBar, CategoryBar, Badge, BarList) and current layout.

**Step 2: Verify in browser**

Navigate to `http://localhost:3000/`. With data in DB, should show live metrics.

**Step 3: Commit**

```bash
git add web/src/app/page.tsx
git commit -m "feat: wire Dashboard page to live API data"
```

---

## Task 12: Update Frontend Tests

**Files:**
- Modify: `web/src/app/__tests__/page.test.tsx`

**Step 1: Update tests to mock api-client**

The existing tests import from `mock-data.ts`. Since pages now use `api-client.ts`, tests need to mock the API functions instead. Use `vi.mock("@/lib/api-client")` to provide mock return values.

Keep the same test assertions (component rendering, accessibility) but change the data source.

**Step 2: Run all frontend tests**

```bash
cd web && npx vitest run
```

Expected: All tests PASS

**Step 3: Commit**

```bash
git add web/src/app/__tests__/
git commit -m "test: update dashboard tests to mock API client"
```

---

## Task 13: Dev Script + Final Verification

**Files:**
- Create: `scripts/dev.sh`

**Step 1: Create dev convenience script**

```bash
#!/usr/bin/env bash
# scripts/dev.sh — Start both API and web servers for development
set -e

echo "Starting eval API on :8001..."
uv run uvicorn eval.api:app --port 8001 --reload &
API_PID=$!

echo "Starting Next.js on :3000..."
cd web && npm run dev &
WEB_PID=$!

trap "kill $API_PID $WEB_PID 2>/dev/null" EXIT
wait
```

**Step 2: Run all Python tests**

```bash
uv run pytest -q
```

Expected: 78 + new API tests = ~90 tests PASS

**Step 3: Run all frontend tests**

```bash
cd web && npx vitest run
```

Expected: All tests PASS

**Step 4: Manual smoke test**

1. Start both servers with `bash scripts/dev.sh`
2. Open `http://localhost:3000`
3. Verify: Dashboard shows empty state (no data yet)
4. Go to Run Tests → verify form appears with model/prompt dropdowns
5. Verify: all pages load without errors

**Step 5: Commit**

```bash
git add scripts/dev.sh
git commit -m "chore: add dev convenience script for dual-server startup"
```

---

## Summary

| Task | Description | Files | Tests |
|------|-------------|-------|-------|
| 1 | Add FastAPI dependencies | pyproject.toml | — |
| 2 | FastAPI read-only endpoints | eval/api.py | 7 |
| 3 | POST comparisons + field reviews | eval/api.py | 3 |
| 4 | POST /api/runs (background execution) | eval/api.py | 2 |
| 5 | Next.js proxy + API client | next.config.ts, api-client.ts | 4 |
| 6 | Wire Run Tests page | runs/page.tsx | — |
| 7 | Wire Review page | review/page.tsx | — |
| 8 | Wire Accuracy Review page | accuracy/page.tsx | — |
| 9 | Wire Leaderboard page | leaderboard/page.tsx | — |
| 10 | Wire Prompt Diff page | prompt-diff/page.tsx | — |
| 11 | Wire Dashboard page | page.tsx | — |
| 12 | Update frontend tests | page.test.tsx | update |
| 13 | Dev script + final verification | scripts/dev.sh | — |

**Total: 13 tasks, ~16 new Python tests, ~4 new TS tests, 13 commits**
