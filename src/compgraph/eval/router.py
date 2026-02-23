from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from compgraph.api.deps import get_db
from compgraph.eval.elo import calculate_elo_ratings
from compgraph.eval.models import (
    EvalComparison,
    EvalCorpus,
    EvalFieldReview,
    EvalResult,
    EvalRun,
)

router = APIRouter()

_CORPUS_PATH = Path(__file__).parent.parent.parent.parent / "eval" / "data" / "corpus.json"

_run_progress: dict[int, dict] = {}
_background_tasks: set[asyncio.Task] = set()

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _run_to_dict(run: EvalRun) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "pass_number": run.pass_number,
        "model": run.model,
        "prompt_version": run.prompt_version,
        "corpus_size": run.corpus_size,
        "total_input_tokens": run.total_input_tokens,
        "total_output_tokens": run.total_output_tokens,
        "total_cost_usd": run.total_cost_usd,
        "total_duration_ms": run.total_duration_ms,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


def _result_to_dict(result: EvalResult) -> dict[str, Any]:
    return {
        "id": str(result.id),
        "run_id": str(result.run_id),
        "posting_id": result.posting_id,
        "raw_response": result.raw_response,
        "parsed_result": result.parsed_result,
        "parse_success": result.parse_success,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cost_usd": result.cost_usd,
        "latency_ms": result.latency_ms,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    }


def _comparison_to_dict(comp: EvalComparison) -> dict[str, Any]:
    return {
        "id": str(comp.id),
        "posting_id": comp.posting_id,
        "result_a_id": str(comp.result_a_id),
        "result_b_id": str(comp.result_b_id),
        "winner": comp.winner,
        "notes": comp.notes,
        "created_at": comp.created_at.isoformat() if comp.created_at else None,
    }


def _field_review_to_dict(fr: EvalFieldReview) -> dict[str, Any]:
    return {
        "id": str(fr.id),
        "result_id": str(fr.result_id),
        "field_name": fr.field_name,
        "model_value": fr.model_value,
        "is_correct": fr.is_correct,
        "correct_value": fr.correct_value,
        "created_at": fr.created_at.isoformat() if fr.created_at else None,
    }


def _corpus_to_dict(entry: EvalCorpus) -> dict[str, Any]:
    return {
        "id": entry.id,
        "company_slug": entry.company_slug,
        "title": entry.title,
        "location": entry.location,
        "full_text": entry.full_text,
        "reference_pass1": entry.reference_pass1,
        "reference_pass2": entry.reference_pass2,
    }


async def _get_run_or_404(run_id: uuid.UUID, db: AsyncSession) -> EvalRun:
    result = await db.execute(select(EvalRun).where(EvalRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


async def _get_result_run_map(db: AsyncSession) -> dict[uuid.UUID, str]:
    stmt = select(EvalResult.id, EvalRun.model, EvalRun.prompt_version).join(
        EvalRun, EvalResult.run_id == EvalRun.id
    )
    rows = (await db.execute(stmt)).all()
    return {row.id: f"{row.model}/{row.prompt_version}" for row in rows}


async def _get_field_accuracy_for_run(db: AsyncSession, run_id: uuid.UUID) -> dict[str, float]:
    stmt = text(
        """
        SELECT fr.field_name,
               AVG(fr.is_correct::float) AS accuracy
        FROM eval_field_reviews fr
        JOIN eval_results r ON fr.result_id = r.id
        WHERE r.run_id = :run_id
          AND fr.is_correct >= 0
        GROUP BY fr.field_name
        """
    )
    rows = (await db.execute(stmt, {"run_id": str(run_id)})).all()
    return {row.field_name: row.accuracy for row in rows}


# --- Corpus ---


@router.get("/corpus")
async def get_corpus(db: DbDep) -> list[dict]:
    rows = (await db.execute(select(EvalCorpus))).scalars().all()
    return [_corpus_to_dict(r) for r in rows]


# --- Runs ---


@router.get("/runs")
async def get_runs(db: DbDep) -> list[dict]:
    rows = (await db.execute(select(EvalRun).order_by(EvalRun.created_at.desc()))).scalars().all()
    return [_run_to_dict(r) for r in rows]


@router.get("/runs/{run_id}")
async def get_run(run_id: uuid.UUID, db: DbDep) -> dict:
    run = await _get_run_or_404(run_id, db)
    return _run_to_dict(run)


@router.delete("/runs/{run_id}")
async def delete_run(run_id: uuid.UUID, db: DbDep) -> dict[str, str]:
    run = await _get_run_or_404(run_id, db)
    await db.delete(run)
    await db.commit()
    return {"status": "deleted"}


@router.get("/runs/{run_id}/results")
async def get_run_results(run_id: uuid.UUID, db: DbDep) -> list[dict]:
    await _get_run_or_404(run_id, db)
    stmt = select(EvalResult).where(EvalResult.run_id == run_id).order_by(EvalResult.posting_id)
    rows = (await db.execute(stmt)).scalars().all()
    return [_result_to_dict(r) for r in rows]


@router.get("/runs/{run_id}/field-accuracy")
async def get_run_field_accuracy(run_id: uuid.UUID, db: DbDep) -> dict[str, float]:
    await _get_run_or_404(run_id, db)
    return await _get_field_accuracy_for_run(db, run_id)


@router.get("/runs/{run_id}/field-reviews")
async def get_run_field_reviews(run_id: uuid.UUID, db: DbDep) -> dict[str, list[dict]]:
    await _get_run_or_404(run_id, db)
    stmt = (
        select(EvalFieldReview)
        .join(EvalResult, EvalFieldReview.result_id == EvalResult.id)
        .where(EvalResult.run_id == run_id)
        .order_by(EvalFieldReview.result_id, EvalFieldReview.field_name)
    )
    rows = (await db.execute(stmt)).scalars().all()
    grouped: dict[str, list[dict]] = {}
    for fr in rows:
        key = str(fr.result_id)
        grouped.setdefault(key, []).append(_field_review_to_dict(fr))
    return grouped


@router.get("/runs/{run_id}/progress")
async def get_run_progress(run_id: uuid.UUID, db: DbDep) -> dict:
    run = await _get_run_or_404(run_id, db)
    run_dict = _run_to_dict(run)
    if run_dict["total_duration_ms"] is not None:
        return {
            "status": "completed",
            "completed": run_dict["corpus_size"],
            "total": run_dict["corpus_size"],
        }
    return {"status": "running", "completed": 0, "total": run_dict["corpus_size"]}


# --- Leaderboard bulk endpoint ---


@router.get("/leaderboard-data")
async def get_leaderboard_data(db: DbDep) -> dict:
    runs = (await db.execute(select(EvalRun).order_by(EvalRun.created_at.desc()))).scalars().all()
    runs_list = [_run_to_dict(r) for r in runs]

    field_accuracy: dict[str, dict[str, float]] = {}
    results: dict[str, list[dict]] = {}

    for run in runs:
        run_id_str = str(run.id)

        field_accuracy[run_id_str] = await _get_field_accuracy_for_run(db, run.id)

        res_stmt = (
            select(EvalResult).where(EvalResult.run_id == run.id).order_by(EvalResult.posting_id)
        )
        res_rows = (await db.execute(res_stmt)).scalars().all()
        results[run_id_str] = [_result_to_dict(r) for r in res_rows]

    comp_rows = (
        (await db.execute(select(EvalComparison).order_by(EvalComparison.created_at)))
        .scalars()
        .all()
    )
    comparisons = [_comparison_to_dict(c) for c in comp_rows]

    run_map = await _get_result_run_map(db)
    elo = (
        calculate_elo_ratings(
            [
                {
                    "result_a_id": c.result_a_id,
                    "result_b_id": c.result_b_id,
                    "winner": c.winner,
                }
                for c in comp_rows
            ],
            run_map,
        )
        if comp_rows
        else {}
    )

    return {
        "runs": runs_list,
        "elo": elo,
        "comparisons": comparisons,
        "field_accuracy": field_accuracy,
        "results": results,
    }


# --- Comparisons ---


@router.get("/comparisons")
async def get_comparisons(db: DbDep) -> list[dict]:
    rows = (
        (await db.execute(select(EvalComparison).order_by(EvalComparison.created_at)))
        .scalars()
        .all()
    )
    return [_comparison_to_dict(c) for c in rows]


# --- ELO ---


@router.get("/elo")
async def get_elo(db: DbDep) -> dict[str, float]:
    comp_rows = (
        (await db.execute(select(EvalComparison).order_by(EvalComparison.created_at)))
        .scalars()
        .all()
    )
    if not comp_rows:
        return {}
    run_map = await _get_result_run_map(db)
    return calculate_elo_ratings(
        [
            {
                "result_a_id": c.result_a_id,
                "result_b_id": c.result_b_id,
                "winner": c.winner,
            }
            for c in comp_rows
        ],
        run_map,
    )


# --- POST: Comparisons ---


class ComparisonCreate(BaseModel):
    posting_id: str
    result_a_id: uuid.UUID
    result_b_id: uuid.UUID
    winner: str
    notes: str | None = None

    @field_validator("winner")
    @classmethod
    def validate_winner(cls, v: str) -> str:
        if v not in ("a", "b", "tie", "both_bad"):
            raise ValueError("winner must be one of: a, b, tie, both_bad")
        return v


@router.post("/comparisons")
async def create_comparison(body: ComparisonCreate, db: DbDep) -> dict[str, str]:
    comp = EvalComparison(
        id=uuid.uuid4(),
        posting_id=body.posting_id,
        result_a_id=body.result_a_id,
        result_b_id=body.result_b_id,
        winner=body.winner,
        notes=body.notes,
    )
    db.add(comp)
    await db.commit()
    await db.refresh(comp)
    return {"id": str(comp.id)}


# --- POST/DELETE: Field Reviews ---


class FieldReviewCreate(BaseModel):
    result_id: uuid.UUID
    field_name: str
    model_value: str | None
    is_correct: Literal[-1, 0, 1]
    correct_value: str | None = None


@router.delete("/field-reviews/{result_id}/{field_name}", status_code=204)
async def delete_field_review(result_id: uuid.UUID, field_name: str, db: DbDep) -> None:
    stmt = delete(EvalFieldReview).where(
        EvalFieldReview.result_id == result_id,
        EvalFieldReview.field_name == field_name,
    )
    await db.execute(stmt)
    await db.commit()


@router.post("/field-reviews")
async def create_field_review(body: FieldReviewCreate, db: DbDep) -> dict[str, str]:
    stmt = text(
        """
        INSERT INTO eval_field_reviews
            (id, result_id, field_name, model_value, is_correct, correct_value)
        VALUES
            (:id, :result_id, :field_name, :model_value, :is_correct, :correct_value)
        ON CONFLICT (result_id, field_name) DO UPDATE SET
            model_value   = EXCLUDED.model_value,
            is_correct    = EXCLUDED.is_correct,
            correct_value = EXCLUDED.correct_value,
            created_at    = now()
        RETURNING id
        """
    )
    row = (
        await db.execute(
            stmt,
            {
                "id": str(uuid.uuid4()),
                "result_id": str(body.result_id),
                "field_name": body.field_name,
                "model_value": body.model_value,
                "is_correct": body.is_correct,
                "correct_value": body.correct_value,
            },
        )
    ).one()
    await db.commit()
    return {"id": str(row.id)}


# --- POST: Run Execution ---


class RunCreate(BaseModel):
    pass_number: int
    model: str
    prompt_version: str
    concurrency: int = Field(default=5, ge=1, le=50)


@router.post("/runs")
async def create_run(body: RunCreate, db: DbDep) -> dict:
    corpus_path = _CORPUS_PATH
    if not corpus_path.exists():
        raise HTTPException(status_code=400, detail="No corpus file found")

    try:
        postings: list[dict] = json.loads(corpus_path.read_text())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load corpus: {exc}") from exc

    run = EvalRun(
        id=uuid.uuid4(),
        pass_number=body.pass_number,
        model=body.model,
        prompt_version=body.prompt_version,
        corpus_size=len(postings),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    tracking_key = run.id.int % (2**53)

    if len(_run_progress) > 100:
        to_delete = [
            k for k, v in _run_progress.items() if v.get("status") in ("completed", "failed")
        ]
        for k in to_delete:
            del _run_progress[k]

    _run_progress[tracking_key] = {
        "status": "starting",
        "completed": 0,
        "total": len(postings),
    }

    # TODO: wire up the actual eval runner once litellm dependency is available (M6)
    # For now, the run record is created so the frontend can track it.

    return {
        "tracking_id": tracking_key,
        "run_id": str(run.id),
        "status": "starting",
        "total": len(postings),
    }


# --- Progress ---


@router.get("/progress/{tracking_id}")
async def get_progress(tracking_id: int) -> dict:
    if tracking_id in _run_progress:
        return _run_progress[tracking_id]
    raise HTTPException(status_code=404, detail="No progress found for this ID")
