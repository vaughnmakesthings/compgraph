"""Pydantic models for structured LLM enrichment output.

Copied from compgraph.enrichment.schemas — kept in sync manually.
Source: src/compgraph/enrichment/schemas.py
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Pass1Result(BaseModel):
    """Structured output from Pass 1 classification."""

    role_archetype: str | None = None
    role_level: str | None = None
    employment_type: str | None = None
    travel_required: bool | None = None

    pay_type: str | None = None
    pay_min: float | None = None
    pay_max: float | None = None
    pay_frequency: str | None = None
    has_commission: bool | None = None
    has_benefits: bool | None = None

    content_role_specific: str | None = None
    content_boilerplate: str | None = None
    content_qualifications: str | None = None
    content_responsibilities: str | None = None

    tools_mentioned: list[str] = Field(default_factory=list)
    kpis_mentioned: list[str] = Field(default_factory=list)
    store_count: int | None = None


class EntityMention(BaseModel):
    """A single entity extracted from a posting."""

    entity_name: str
    entity_type: str
    confidence: float = Field(ge=0.0, le=1.0)


class Pass2Result(BaseModel):
    """Structured output from Pass 2 entity extraction."""

    entities: list[EntityMention] = Field(default_factory=list)
