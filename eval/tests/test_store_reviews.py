"""Tests for field review CRUD in EvalStore."""

from pathlib import Path

import pytest_asyncio
from eval.store import EvalStore


@pytest_asyncio.fixture
async def store(tmp_path: Path):
    """Create a temporary store with a run and result for testing reviews."""
    s = EvalStore(str(tmp_path / "test.db"))
    await s.init()
    await s.insert_corpus(
        [
            {
                "id": "p1",
                "company_slug": "bds",
                "title": "Rep",
                "location": "NY",
                "full_text": "Text",
            }
        ]
    )
    yield s
    await s.close()


async def _setup_run_and_result(store: EvalStore) -> tuple[int, int]:
    """Helper: create a run and result, return (run_id, result_id)."""
    run_id = await store.create_run(1, "haiku-4.5", "pass1_v1", 1)
    result_id = await store.insert_result(
        run_id, "p1", "{}", {"role_archetype": "field_rep"}, True, 100, 50, 0.001, 500
    )
    return run_id, result_id


async def test_field_reviews_table_created(store: EvalStore):
    """init() should create the field_reviews table."""
    tables = await store.list_tables()
    assert "field_reviews" in tables


async def test_upsert_field_review_insert(store: EvalStore):
    """Should insert a new field review."""
    _, result_id = await _setup_run_and_result(store)

    review_id = await store.upsert_field_review(
        result_id=result_id,
        field_name="role_archetype",
        model_value='"field_rep"',
        is_correct=1,
    )
    assert review_id > 0

    reviews = await store.get_field_reviews(result_id)
    assert len(reviews) == 1
    assert reviews[0]["field_name"] == "role_archetype"
    assert reviews[0]["is_correct"] == 1
    assert reviews[0]["correct_value"] is None


async def test_upsert_field_review_update(store: EvalStore):
    """Upserting the same field should update the existing review."""
    _, result_id = await _setup_run_and_result(store)

    # Insert as correct
    await store.upsert_field_review(
        result_id=result_id,
        field_name="role_archetype",
        model_value='"field_rep"',
        is_correct=1,
    )

    # Update to wrong with correction
    await store.upsert_field_review(
        result_id=result_id,
        field_name="role_archetype",
        model_value='"field_rep"',
        is_correct=0,
        correct_value='"merchandiser"',
    )

    reviews = await store.get_field_reviews(result_id)
    assert len(reviews) == 1
    assert reviews[0]["is_correct"] == 0
    assert reviews[0]["correct_value"] == '"merchandiser"'


async def test_get_field_accuracy(store: EvalStore):
    """Should compute per-field accuracy from reviews."""
    run_id, result_id = await _setup_run_and_result(store)

    await store.upsert_field_review(result_id, "role_archetype", '"field_rep"', 1)
    await store.upsert_field_review(result_id, "role_level", '"entry"', 0, '"mid"')
    await store.upsert_field_review(result_id, "pay_type", '"hourly"', 1)

    accuracy = await store.get_field_accuracy(run_id)
    assert accuracy["role_archetype"] == 1.0
    assert accuracy["role_level"] == 0.0
    assert accuracy["pay_type"] == 1.0


async def test_get_reviewed_count(store: EvalStore):
    """Should count distinct results that have reviews."""
    run_id, result_id = await _setup_run_and_result(store)

    # No reviews yet
    count = await store.get_reviewed_count(run_id)
    assert count == 0

    # Add reviews for one result
    await store.upsert_field_review(result_id, "role_archetype", '"field_rep"', 1)
    await store.upsert_field_review(result_id, "role_level", '"entry"', 1)

    count = await store.get_reviewed_count(run_id)
    assert count == 1


async def test_find_run(store: EvalStore):
    """find_run should return existing run or None."""
    run_id = await store.create_run(1, "haiku-4.5", "pass1_v1", 10)

    found = await store.find_run(1, "haiku-4.5", "pass1_v1")
    assert found is not None
    assert found["id"] == run_id

    not_found = await store.find_run(1, "gpt-4o-mini", "pass1_v1")
    assert not_found is None
