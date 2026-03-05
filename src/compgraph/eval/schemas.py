from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from compgraph.enrichment.schemas import Pass1Result, Pass2Result


class EvalRunResponse(BaseModel):
    id: uuid.UUID
    pass_number: int
    model: str
    prompt_version: str
    corpus_size: int
    total_input_tokens: int | None = None
    total_output_tokens: int | None = None
    total_cost_usd: float | None = None
    total_duration_ms: int | None = None
    created_at: datetime
    status: Literal["starting", "running", "completed"] = "starting"
    total_items: int = 0
    completed_items: int = 0

    model_config = {"from_attributes": True}


class EvalSampleResponse(BaseModel):
    id: str
    company_slug: str
    title: str
    location: str | None = None
    full_text: str
    reference_pass1: dict | None = None
    reference_pass2: dict | None = None

    model_config = {"from_attributes": True}


class EvalResultResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    posting_id: str
    raw_response: str | None = None
    parsed_result: dict | None = None
    parse_success: bool
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvalComparisonResponse(BaseModel):
    id: uuid.UUID
    posting_id: str
    result_a_id: uuid.UUID
    result_b_id: uuid.UUID
    winner: str
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvalFieldReviewResponse(BaseModel):
    id: uuid.UUID
    result_id: uuid.UUID
    field_name: str
    model_value: str | None = None
    is_correct: int
    correct_value: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvalRunCreateRequest(BaseModel):
    pass_number: int = Field(ge=1, le=2)
    model: str
    prompt_version: str
    concurrency: int = Field(default=5, ge=1, le=50)


class EvalComparisonCreateRequest(BaseModel):
    posting_id: str
    result_a_id: uuid.UUID
    result_b_id: uuid.UUID
    winner: Literal["a", "b", "tie", "both_bad"]
    notes: str | None = None


class EvalFieldReviewCreateRequest(BaseModel):
    result_id: uuid.UUID
    field_name: str
    model_value: str | None = None
    is_correct: Literal[-1, 0, 1]
    correct_value: str | None = None


class EvalRunProgressResponse(BaseModel):
    status: Literal["starting", "running", "completed", "failed"]
    completed: int = 0
    total: int = 0


class EvalModelInfo(BaseModel):
    id: str
    label: str


__all__ = [
    "EvalComparisonCreateRequest",
    "EvalComparisonResponse",
    "EvalFieldReviewCreateRequest",
    "EvalFieldReviewResponse",
    "EvalModelInfo",
    "EvalResultResponse",
    "EvalRunCreateRequest",
    "EvalRunProgressResponse",
    "EvalRunResponse",
    "EvalSampleResponse",
    "Pass1Result",
    "Pass2Result",
]
