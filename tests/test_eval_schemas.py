from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from compgraph.eval.config import MODELS, SUPPORTED_MODEL_IDS, SUPPORTED_MODELS
from compgraph.eval.schemas import (
    EvalComparisonCreateRequest,
    EvalComparisonResponse,
    EvalFieldReviewCreateRequest,
    EvalFieldReviewResponse,
    EvalModelInfo,
    EvalResultResponse,
    EvalRunCreateRequest,
    EvalRunProgressResponse,
    EvalRunResponse,
    EvalSampleResponse,
    Pass1Result,
    Pass2Result,
)


class TestEvalConfig:
    def test_models_dict_maps_alias_to_full_id(self) -> None:
        assert "haiku-4.5" in MODELS
        assert MODELS["haiku-4.5"] == "claude-haiku-4-5-20251001"

    def test_models_aliases_all_present(self) -> None:
        expected = {"haiku-4.5", "sonnet-4.5", "sonnet-4.6", "opus-4.6"}
        assert set(MODELS.keys()) == expected

    def test_supported_models_has_entries(self) -> None:
        assert len(SUPPORTED_MODELS) > 0
        for entry in SUPPORTED_MODELS:
            assert "id" in entry
            assert "label" in entry

    def test_supported_model_ids_matches_list(self) -> None:
        ids_from_list = {m["id"] for m in SUPPORTED_MODELS}
        assert SUPPORTED_MODEL_IDS == ids_from_list

    def test_all_model_aliases_in_supported(self) -> None:
        for full_id in MODELS.values():
            assert full_id in SUPPORTED_MODEL_IDS


class TestEvalRunResponse:
    def test_valid_response(self) -> None:
        now = datetime.now(UTC)
        resp = EvalRunResponse(
            id=uuid.uuid4(),
            pass_number=1,
            model="claude-haiku-4-5-20251001",
            prompt_version="v1",
            corpus_size=50,
            created_at=now,
            status="completed",
            total_items=50,
            completed_items=50,
        )
        assert resp.pass_number == 1
        assert resp.status == "completed"
        assert resp.total_cost_usd is None

    def test_defaults(self) -> None:
        now = datetime.now(UTC)
        resp = EvalRunResponse(
            id=uuid.uuid4(),
            pass_number=2,
            model="test",
            prompt_version="v1",
            corpus_size=10,
            created_at=now,
        )
        assert resp.status == "starting"
        assert resp.total_items == 0
        assert resp.completed_items == 0


class TestEvalSampleResponse:
    def test_valid_sample(self) -> None:
        sample = EvalSampleResponse(
            id="posting_abc",
            company_slug="acosta",
            title="Brand Ambassador",
            full_text="Some job description text",
        )
        assert sample.location is None
        assert sample.reference_pass1 is None

    def test_with_references(self) -> None:
        sample = EvalSampleResponse(
            id="posting_xyz",
            company_slug="premium",
            title="Merchandiser",
            full_text="Full text here",
            reference_pass1={"role_archetype": "merchandiser"},
            reference_pass2={"entities": []},
        )
        assert sample.reference_pass1 is not None


class TestEvalResultResponse:
    def test_valid_result(self) -> None:
        now = datetime.now(UTC)
        result = EvalResultResponse(
            id=uuid.uuid4(),
            run_id=uuid.uuid4(),
            posting_id="posting_abc",
            parse_success=True,
            parsed_result={"role_archetype": "field_rep"},
            created_at=now,
        )
        assert result.parse_success is True
        assert result.raw_response is None


class TestEvalComparisonResponse:
    def test_valid_comparison(self) -> None:
        now = datetime.now(UTC)
        comp = EvalComparisonResponse(
            id=uuid.uuid4(),
            posting_id="posting_abc",
            result_a_id=uuid.uuid4(),
            result_b_id=uuid.uuid4(),
            winner="a",
            created_at=now,
        )
        assert comp.notes is None


class TestEvalFieldReviewResponse:
    def test_valid_field_review(self) -> None:
        now = datetime.now(UTC)
        fr = EvalFieldReviewResponse(
            id=uuid.uuid4(),
            result_id=uuid.uuid4(),
            field_name="role_archetype",
            is_correct=1,
            created_at=now,
        )
        assert fr.model_value is None
        assert fr.correct_value is None


class TestEvalRunCreateRequest:
    def test_valid_create(self) -> None:
        req = EvalRunCreateRequest(
            pass_number=1,
            model="claude-haiku-4-5-20251001",
            prompt_version="v1",
        )
        assert req.concurrency == 5

    def test_invalid_pass_number(self) -> None:
        with pytest.raises(ValidationError):
            EvalRunCreateRequest(
                pass_number=3,
                model="test",
                prompt_version="v1",
            )

    def test_concurrency_bounds(self) -> None:
        with pytest.raises(ValidationError):
            EvalRunCreateRequest(
                pass_number=1,
                model="test",
                prompt_version="v1",
                concurrency=0,
            )
        with pytest.raises(ValidationError):
            EvalRunCreateRequest(
                pass_number=1,
                model="test",
                prompt_version="v1",
                concurrency=51,
            )


class TestEvalComparisonCreateRequest:
    def test_valid_winners(self) -> None:
        for winner in ("a", "b", "tie", "both_bad"):
            req = EvalComparisonCreateRequest(
                posting_id="p1",
                result_a_id=uuid.uuid4(),
                result_b_id=uuid.uuid4(),
                winner=winner,
            )
            assert req.winner == winner

    def test_invalid_winner(self) -> None:
        with pytest.raises(ValidationError):
            EvalComparisonCreateRequest(
                posting_id="p1",
                result_a_id=uuid.uuid4(),
                result_b_id=uuid.uuid4(),
                winner="invalid",
            )


class TestEvalFieldReviewCreateRequest:
    def test_valid_is_correct_values(self) -> None:
        for val in (-1, 0, 1):
            req = EvalFieldReviewCreateRequest(
                result_id=uuid.uuid4(),
                field_name="role_archetype",
                is_correct=val,
            )
            assert req.is_correct == val

    def test_invalid_is_correct(self) -> None:
        with pytest.raises(ValidationError):
            EvalFieldReviewCreateRequest(
                result_id=uuid.uuid4(),
                field_name="role_archetype",
                is_correct=2,
            )


class TestEvalRunProgressResponse:
    def test_defaults(self) -> None:
        prog = EvalRunProgressResponse(status="starting")
        assert prog.completed == 0
        assert prog.total == 0


class TestEvalModelInfo:
    def test_valid(self) -> None:
        info = EvalModelInfo(id="claude-haiku-4-5-20251001", label="Haiku 4.5")
        assert info.id == "claude-haiku-4-5-20251001"


class TestEnrichmentSchemaReexport:
    def test_pass1_result_importable(self) -> None:
        result = Pass1Result(role_archetype="field_rep")
        assert result.role_archetype == "field_rep"

    def test_pass2_result_importable(self) -> None:
        result = Pass2Result(entities=[])
        assert result.entities == []
