import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class EvalBase(DeclarativeBase):
    pass


class EvalCorpus(EvalBase):
    __tablename__ = "eval_corpus"

    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    company_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    reference_pass1: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reference_pass2: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    results: Mapped[list["EvalResult"]] = relationship(back_populates="corpus_entry")


class EvalRun(EvalBase):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pass_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    corpus_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    results: Mapped[list["EvalResult"]] = relationship(back_populates="run")

    __table_args__ = (
        CheckConstraint("pass_number IN (1, 2)", name="check_eval_runs_pass_number"),
        Index("ix_eval_runs_pass_model", "pass_number", "model"),
    )


class EvalResult(EvalBase):
    __tablename__ = "eval_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eval_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    posting_id: Mapped[str] = mapped_column(
        String(200),
        ForeignKey("eval_corpus.id"),
        nullable=False,
    )
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    parse_success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    run: Mapped["EvalRun"] = relationship(back_populates="results")
    corpus_entry: Mapped["EvalCorpus"] = relationship(back_populates="results")
    field_reviews: Mapped[list["EvalFieldReview"]] = relationship(back_populates="result")

    __table_args__ = (
        UniqueConstraint("run_id", "posting_id", name="uq_eval_results_run_posting"),
        Index("ix_eval_results_run_id", "run_id"),
    )


class EvalComparison(EvalBase):
    __tablename__ = "eval_comparisons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    posting_id: Mapped[str] = mapped_column(
        String(200),
        ForeignKey("eval_corpus.id"),
        nullable=False,
    )
    result_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eval_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    result_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eval_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    winner: Mapped[str] = mapped_column(String(10), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    __table_args__ = (
        CheckConstraint(
            "winner IN ('a', 'b', 'tie', 'both_bad')",
            name="check_eval_comparisons_winner",
        ),
        Index("ix_eval_comparisons_posting_id", "posting_id"),
    )


class EvalFieldReview(EvalBase):
    __tablename__ = "eval_field_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eval_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    result: Mapped["EvalResult"] = relationship(back_populates="field_reviews")

    __table_args__ = (
        UniqueConstraint("result_id", "field_name", name="uq_eval_field_reviews_result_field"),
        Index("ix_eval_field_reviews_result_id", "result_id"),
    )
