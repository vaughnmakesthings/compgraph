"""Pydantic models for structured LLM enrichment output."""

from __future__ import annotations

import logging
from typing import Literal, Self, get_args

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

logger = logging.getLogger(__name__)

# Canonical values for LLM-generated categorical fields.
# Used in Literal types to catch hallucination at parse time.
RoleArchetype = Literal[
    "field_rep",
    "merchandiser",
    "brand_ambassador",
    "demo_specialist",
    "team_lead",
    "manager",
    "recruiter",
    "corporate",
    "other",
]
RoleLevel = Literal["entry", "mid", "senior", "lead", "manager", "director"]
EmploymentType = Literal["full_time", "part_time", "contract", "seasonal", "intern"]
PayType = Literal["hourly", "salary", "commission"]
PayFrequency = Literal["hour", "week", "month", "year"]
EntityType = Literal["client_brand", "retailer", "ambiguous"]

# Pay range bounds per frequency period.
# Guards against LLM extracting non-salary figures (e.g. "$1M budget").
PAY_RANGE_BY_FREQUENCY: dict[str | None, tuple[float, float]] = {
    "hour": (10.0, 150.0),
    "week": (400.0, 6_000.0),
    "month": (1_667.0, 25_000.0),
    "year": (20_000.0, 300_000.0),
    None: (10.0, 300_000.0),
}


def _coerce_literal(value: str | None, allowed: set[str], field_name: str) -> str | None:
    if value is not None and value not in allowed:
        logger.warning(
            "Unexpected %s value from LLM: %r (allowed: %s) — coercing to None",
            field_name,
            value,
            allowed,
        )
        return None
    return value


class Pass1Result(BaseModel):
    """Structured output from Pass 1 (Haiku) classification.

    Maps directly to PostingEnrichment columns. All fields are optional
    because not every posting contains every data point.
    """

    role_archetype: RoleArchetype | None = Field(
        None,
        description=(
            "Primary role category. One of: field_rep, merchandiser, "
            "brand_ambassador, demo_specialist, team_lead, manager, "
            "recruiter, corporate, other"
        ),
    )
    role_level: RoleLevel | None = Field(
        None,
        description="Seniority level. One of: entry, mid, senior, lead, manager, director",
    )
    employment_type: EmploymentType | None = Field(
        None,
        description="Employment type. One of: full_time, part_time, contract, seasonal, intern",
    )
    travel_required: bool | None = Field(None, description="Whether the role requires travel")

    # Compensation
    pay_type: PayType | None = Field(
        None, description="Pay structure. One of: hourly, salary, commission"
    )
    pay_min: float | None = Field(None, description="Minimum pay amount")
    pay_max: float | None = Field(None, description="Maximum pay amount")
    pay_frequency: PayFrequency | None = Field(
        None,
        description="Pay period. One of: hour, week, month, year",
    )

    @field_validator("role_archetype", mode="before")
    @classmethod
    def _check_role_archetype(cls, v: str | None) -> str | None:
        return _coerce_literal(v, set(get_args(RoleArchetype)), "role_archetype")

    @field_validator("role_level", mode="before")
    @classmethod
    def _check_role_level(cls, v: str | None) -> str | None:
        return _coerce_literal(v, set(get_args(RoleLevel)), "role_level")

    @field_validator("employment_type", mode="before")
    @classmethod
    def _check_employment_type(cls, v: str | None) -> str | None:
        return _coerce_literal(v, set(get_args(EmploymentType)), "employment_type")

    @field_validator("pay_type", mode="before")
    @classmethod
    def _check_pay_type(cls, v: str | None) -> str | None:
        return _coerce_literal(v, set(get_args(PayType)), "pay_type")

    @field_validator("pay_frequency", mode="before")
    @classmethod
    def _check_pay_frequency(cls, v: str | None) -> str | None:
        return _coerce_literal(v, set(get_args(PayFrequency)), "pay_frequency")

    @model_validator(mode="after")
    def _validate_pay_range(self) -> Self:
        floor, ceiling = PAY_RANGE_BY_FREQUENCY[self.pay_frequency]

        if self.pay_min is not None and not (floor <= self.pay_min <= ceiling):
            raise ValueError(
                f"pay_min {self.pay_min} outside allowed range "
                f"[{floor}, {ceiling}] for frequency={self.pay_frequency!r}"
            )

        if self.pay_max is not None and not (floor <= self.pay_max <= ceiling):
            raise ValueError(
                f"pay_max {self.pay_max} outside allowed range "
                f"[{floor}, {ceiling}] for frequency={self.pay_frequency!r}"
            )

        if self.pay_min is not None and self.pay_max is not None and self.pay_min > self.pay_max:
            raise ValueError(f"pay_min ({self.pay_min}) must not exceed pay_max ({self.pay_max})")

        return self

    has_commission: bool | None = Field(None, description="Whether commission/bonus is mentioned")
    has_benefits: bool | None = Field(None, description="Whether benefits are mentioned")

    # Content sections
    content_role_specific: str | None = Field(
        None,
        description="Role-specific responsibilities and requirements (not boilerplate)",
    )
    content_boilerplate: str | None = Field(
        None,
        description="Generic company boilerplate text (EEO, about the company, etc.)",
    )
    content_qualifications: str | None = Field(
        None,
        description="Required and preferred qualifications",
    )
    content_responsibilities: str | None = Field(
        None,
        description="Day-to-day responsibilities and duties",
    )

    # Metadata
    tools_mentioned: list[str] = Field(
        default_factory=list,
        description="Software tools, apps, or platforms mentioned",
    )
    kpis_mentioned: list[str] = Field(
        default_factory=list,
        description="Performance metrics or KPIs mentioned",
    )
    store_count: int | None = Field(None, description="Number of stores or locations mentioned")


# Make ValidationError available for import from this module
__all__ = [
    "PAY_RANGE_BY_FREQUENCY",
    "EmploymentType",
    "EntityMention",
    "EntityType",
    "Pass1Result",
    "Pass2Result",
    "PayFrequency",
    "PayType",
    "RoleArchetype",
    "RoleLevel",
    "ValidationError",
]
# ---------------------------------------------------------------------------
# Pass 2 schemas — Entity Extraction (Sonnet)
# ---------------------------------------------------------------------------


class EntityMention(BaseModel):
    """A single entity (brand or retailer) extracted from a posting."""

    entity_name: str = Field(description="Name of the entity as it appears in the text")
    entity_type: EntityType = Field(
        description=(
            "Classification of the entity. One of: "
            "client_brand (company whose products are represented), "
            "retailer (store where reps deploy), "
            "ambiguous (could be either)"
        ),
    )

    @field_validator("entity_type", mode="before")
    @classmethod
    def _check_entity_type(cls, v: str) -> str:
        if v not in set(get_args(EntityType)):
            logger.warning("Unexpected entity_type from LLM: %r — coercing to 'ambiguous'", v)
            return "ambiguous"
        return v

    confidence: float = Field(
        description="Confidence score from 0.0 to 1.0",
        ge=0.0,
        le=1.0,
    )


class Pass2Result(BaseModel):
    """Structured output from Pass 2 (Sonnet) entity extraction."""

    entities: list[EntityMention] = Field(
        default_factory=list,
        description="List of brand and retailer entities found in the posting",
    )
