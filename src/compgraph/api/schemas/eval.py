from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class EvalCorpusItem(BaseModel):
    id: str
    company_slug: str
    title: str
    location: str | None = None
    full_text: str
    reference_pass1: dict[str, Any] | None = None
    reference_pass2: dict[str, Any] | None = None


class EvalRunItem(BaseModel):
    id: str
    pass_number: int
    model: str
    prompt_version: str
    corpus_size: int
    total_input_tokens: int | None = None
    total_output_tokens: int | None = None
    total_cost_usd: float | None = None
    total_duration_ms: int | None = None
    created_at: str | None = None
    status: str
    total_items: int
    completed_items: int
    completed_at: None = None


class EvalResultItem(BaseModel):
    id: str
    run_id: str
    posting_id: str
    raw_response: str | None = None
    parsed_result: dict[str, Any] | None = None
    parse_success: bool
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
    created_at: str | None = None


class EvalComparisonItem(BaseModel):
    id: str
    posting_id: str
    result_a_id: str
    result_b_id: str
    winner: str
    notes: str | None = None
    created_at: str | None = None


class EvalFieldReviewItem(BaseModel):
    id: str
    result_id: str
    field_name: str
    model_value: str | None = None
    is_correct: Literal[-1, 0, 1]
    correct_value: str | None = None
    created_at: str | None = None


class EvalModelItem(BaseModel):
    id: str
    label: str


class EvalLeaderboardResponse(BaseModel):
    runs: list[EvalRunItem]
    elo: dict[str, float]
    comparisons: list[EvalComparisonItem]
    field_accuracy: dict[str, dict[str, float]]
    results: dict[str, list[EvalResultItem]]


class EvalRunCreateResponse(BaseModel):
    tracking_id: int
    run_id: str
    status: str
    total: int


class IdResponse(BaseModel):
    id: str


class StatusResponse(BaseModel):
    status: str
