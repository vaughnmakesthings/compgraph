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
from pydantic import BaseModel, Field, field_validator

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

# Strong references to background tasks to prevent GC collection
_background_tasks: set[asyncio.Task] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _store
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _store = EvalStore(os.environ.get("EVAL_DB_PATH", DB_PATH))
    await _store.init()
    yield
    await _store.close()


app = FastAPI(title="CompGraph Eval API", lifespan=lifespan)


def get_store() -> EvalStore:
    if _store is None:
        raise RuntimeError("Store not initialized — lifespan not started")
    return _store


# --- Config ---


@app.get("/api/config/models")
async def get_models() -> dict[str, str]:
    return MODELS


@app.get("/api/config/prompts/{pass_number}")
async def get_prompts(pass_number: int) -> list[str]:
    return list_prompts(pass_number)


# --- Runs ---


@app.get("/api/runs")
async def get_runs() -> list[dict]:
    store = get_store()
    return await store.get_all_runs()


@app.get("/api/runs/{run_id}")
async def get_run(run_id: int) -> dict:
    store = get_store()
    run = await store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.delete("/api/runs/{run_id}")
async def delete_run(run_id: int) -> dict[str, str]:
    store = get_store()
    run = await store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    await store.delete_run(run_id)
    return {"status": "deleted"}


@app.get("/api/runs/{run_id}/results")
async def get_run_results(run_id: int) -> list[dict]:
    store = get_store()
    run = await store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return await store.get_results(run_id)


@app.get("/api/runs/{run_id}/field-accuracy")
async def get_run_field_accuracy(run_id: int) -> dict[str, float]:
    store = get_store()
    run = await store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return await store.get_field_accuracy(run_id)


@app.get("/api/runs/{run_id}/field-reviews")
async def get_run_field_reviews(run_id: int) -> dict[str, list[dict]]:
    store = get_store()
    run = await store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    reviews = await store.get_all_field_reviews_for_run(run_id)
    # Convert int keys to strings for JSON serialization
    return {str(k): v for k, v in reviews.items()}


@app.get("/api/runs/{run_id}/progress")
async def get_run_progress(run_id: int) -> dict:
    if run_id in _run_progress:
        return _run_progress[run_id]
    store = get_store()
    run = await store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    # Only report completed if the run has finished (has duration set)
    if run["total_duration_ms"] is not None:
        return {
            "status": "completed",
            "completed": run["corpus_size"],
            "total": run["corpus_size"],
        }
    return {"status": "running", "completed": 0, "total": run["corpus_size"]}


# --- Bulk: Leaderboard data ---


@app.get("/api/leaderboard-data")
async def get_leaderboard_data() -> dict:
    """Bulk endpoint returning all data the leaderboard page needs in one request."""
    store = get_store()
    runs = await store.get_all_runs()

    field_accuracy: dict[int, dict[str, float]] = {}
    results: dict[int, list[dict]] = {}
    for run in runs:
        run_id = run["id"]
        field_accuracy[run_id] = await store.get_field_accuracy(run_id)
        results[run_id] = await store.get_results(run_id)

    comparisons = await store.get_comparisons()
    run_map = await store.get_result_run_map()
    elo = calculate_elo_ratings(comparisons, run_map) if comparisons else {}

    return {
        "runs": runs,
        "elo": elo,
        "comparisons": comparisons,
        "field_accuracy": {str(k): v for k, v in field_accuracy.items()},
        "results": {str(k): v for k, v in results.items()},
    }


# --- Corpus ---


@app.get("/api/corpus")
async def get_corpus() -> list[dict]:
    store = get_store()
    return await store.get_corpus()


# --- Comparisons ---


@app.get("/api/comparisons")
async def get_comparisons() -> list[dict]:
    store = get_store()
    return await store.get_comparisons()


# --- Elo ---


@app.get("/api/elo")
async def get_elo() -> dict[str, float]:
    store = get_store()
    comparisons = await store.get_comparisons()
    if not comparisons:
        return {}
    run_map = await store.get_result_run_map()
    return calculate_elo_ratings(comparisons, run_map)


# --- POST: Comparisons ---


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


@app.post("/api/comparisons")
async def create_comparison(body: ComparisonCreate) -> dict[str, int]:
    store = get_store()
    comp_id = await store.insert_comparison(
        posting_id=body.posting_id,
        result_a_id=body.result_a_id,
        result_b_id=body.result_b_id,
        winner=body.winner,
        notes=body.notes,
    )
    return {"id": comp_id}


# --- POST: Field Reviews ---


class FieldReviewCreate(BaseModel):
    result_id: int
    field_name: str
    model_value: str | None
    is_correct: int
    correct_value: str | None = None


@app.delete("/api/field-reviews/{result_id}/{field_name}", status_code=204)
async def delete_field_review(result_id: int, field_name: str) -> None:
    store = get_store()
    await store.delete_field_review(result_id, field_name)


@app.post("/api/field-reviews")
async def create_field_review(body: FieldReviewCreate) -> dict[str, int]:
    store = get_store()
    review_id = await store.upsert_field_review(
        result_id=body.result_id,
        field_name=body.field_name,
        model_value=body.model_value,
        is_correct=body.is_correct,
        correct_value=body.correct_value,
    )
    return {"id": review_id}


# --- POST: Run Execution ---


class RunCreate(BaseModel):
    pass_number: int
    model: str
    prompt_version: str
    concurrency: int = Field(default=5, ge=1, le=50)


@app.post("/api/runs")
async def create_run(body: RunCreate) -> dict:
    if body.model not in MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown model: {body.model}")

    corpus_path = os.environ.get("EVAL_CORPUS_PATH", CORPUS_PATH)
    if not Path(corpus_path).exists():
        raise HTTPException(status_code=400, detail="No corpus file found")

    # Evict completed/failed entries when progress dict grows too large
    if len(_run_progress) > 100:
        to_delete = [
            k
            for k, v in _run_progress.items()
            if v.get("status") in ("completed", "failed")
        ]
        for k in to_delete:
            del _run_progress[k]

    store = get_store()
    from eval.runner import load_corpus, run_evaluation

    postings = load_corpus(corpus_path)
    import uuid

    tracking_key = uuid.uuid4().int % (2**53)  # Safe JS integer range
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
            completed_data = {
                "status": "completed",
                "run_id": summary.run_id,
                "completed": summary.total,
                "total": summary.total,
                "succeeded": summary.succeeded,
                "failed": summary.failed,
                "cost_usd": summary.total_cost_usd,
                "duration_ms": summary.total_duration_ms,
            }
            _run_progress[tracking_key] = completed_data
            _run_progress[summary.run_id] = completed_data
        except Exception as e:
            _run_progress[tracking_key] = {"status": "failed", "error": str(e)}

    task = asyncio.create_task(_execute())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"tracking_id": tracking_key, "status": "starting", "total": len(postings)}


# --- Progress ---


@app.get("/api/progress/{tracking_id}")
async def get_progress(tracking_id: int) -> dict:
    if tracking_id in _run_progress:
        return _run_progress[tracking_id]
    raise HTTPException(status_code=404, detail="No progress found for this ID")
