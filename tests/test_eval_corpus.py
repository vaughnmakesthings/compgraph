from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime
from unittest.mock import MagicMock

from scripts.generate_eval_corpus import (
    CORPUS_MAX_TEXT_LENGTH,
    build_corpus_query,
    rows_to_corpus,
)


def _make_posting(posting_id: uuid.UUID | None = None) -> MagicMock:
    p = MagicMock()
    p.id = posting_id or uuid.uuid4()
    p.company_id = uuid.uuid4()
    p.is_active = True
    p.first_seen_at = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    return p


def _make_snapshot(
    title: str | None = "Field Sales Rep",
    location: str | None = "Atlanta, GA",
    full_text: str | None = "We are hiring a field sales rep...",
) -> MagicMock:
    s = MagicMock()
    s.title_raw = title
    s.location_raw = location
    s.full_text_raw = full_text
    s.snapshot_date = date(2024, 6, 15)
    return s


class TestBuildCorpusQuery:
    def test_returns_select_statement(self) -> None:
        q = build_corpus_query()
        compiled = str(q.compile(compile_kwargs={"literal_binds": True}))
        assert "postings" in compiled.lower()
        assert "posting_snapshots" in compiled.lower()
        assert "companies" in compiled.lower()

    def test_applies_company_slug_filter(self) -> None:
        q = build_corpus_query(company_slug="bds")
        compiled = str(q.compile(compile_kwargs={"literal_binds": True}))
        assert "bds" in compiled

    def test_applies_limit(self) -> None:
        q = build_corpus_query(limit=50)
        compiled = str(q.compile(compile_kwargs={"literal_binds": True}))
        assert "50" in compiled

    def test_no_company_slug_omits_filter(self) -> None:
        q = build_corpus_query(company_slug=None)
        compiled = str(q.compile(compile_kwargs={"literal_binds": True}))
        assert "slug" not in compiled.split("WHERE")[1] if "WHERE" in compiled else True


class TestRowsToCorpus:
    def test_empty_rows(self) -> None:
        assert rows_to_corpus([]) == []

    def test_single_row(self) -> None:
        posting_id = uuid.uuid4()
        posting = _make_posting(posting_id=posting_id)
        snapshot = _make_snapshot()
        rows = [(posting, snapshot, "bds")]

        corpus = rows_to_corpus(rows)

        assert len(corpus) == 1
        item = corpus[0]
        assert item["id"] == f"posting_{posting_id}"
        assert item["company_slug"] == "bds"
        assert item["title"] == "Field Sales Rep"
        assert item["location"] == "Atlanta, GA"
        assert item["full_text"] == "We are hiring a field sales rep..."
        assert item["reference_pass1"] is None
        assert item["reference_pass2"] is None

    def test_multiple_rows(self) -> None:
        rows = [
            (_make_posting(), _make_snapshot(), "bds"),
            (_make_posting(), _make_snapshot(title="Manager"), "advantage"),
            (_make_posting(), _make_snapshot(title="Coordinator"), "marketsource"),
        ]
        corpus = rows_to_corpus(rows)
        assert len(corpus) == 3
        slugs = [item["company_slug"] for item in corpus]
        assert slugs == ["bds", "advantage", "marketsource"]

    def test_null_title_defaults_to_empty(self) -> None:
        rows = [(_make_posting(), _make_snapshot(title=None), "bds")]
        corpus = rows_to_corpus(rows)
        assert corpus[0]["title"] == ""

    def test_null_location_defaults_to_empty(self) -> None:
        rows = [(_make_posting(), _make_snapshot(location=None), "bds")]
        corpus = rows_to_corpus(rows)
        assert corpus[0]["location"] == ""

    def test_null_full_text_defaults_to_empty(self) -> None:
        rows = [(_make_posting(), _make_snapshot(full_text=None), "bds")]
        corpus = rows_to_corpus(rows)
        assert corpus[0]["full_text"] == ""

    def test_full_text_truncated_at_max_length(self) -> None:
        long_text = "x" * (CORPUS_MAX_TEXT_LENGTH + 5000)
        rows = [(_make_posting(), _make_snapshot(full_text=long_text), "bds")]
        corpus = rows_to_corpus(rows)
        assert len(corpus[0]["full_text"]) == CORPUS_MAX_TEXT_LENGTH

    def test_full_text_under_limit_not_truncated(self) -> None:
        text = "Short description"
        rows = [(_make_posting(), _make_snapshot(full_text=text), "bds")]
        corpus = rows_to_corpus(rows)
        assert corpus[0]["full_text"] == text

    def test_posting_id_format(self) -> None:
        pid = uuid.uuid4()
        rows = [(_make_posting(posting_id=pid), _make_snapshot(), "bds")]
        corpus = rows_to_corpus(rows)
        assert corpus[0]["id"].startswith("posting_")
        assert str(pid) in corpus[0]["id"]

    def test_corpus_json_serializable(self) -> None:
        rows = [(_make_posting(), _make_snapshot(), "bds")]
        corpus = rows_to_corpus(rows)
        serialized = json.dumps(corpus)
        deserialized = json.loads(serialized)
        assert len(deserialized) == 1
        assert deserialized[0]["company_slug"] == "bds"

    def test_all_null_fields(self) -> None:
        rows = [(_make_posting(), _make_snapshot(title=None, location=None, full_text=None), "bds")]
        corpus = rows_to_corpus(rows)
        item = corpus[0]
        assert item["title"] == ""
        assert item["location"] == ""
        assert item["full_text"] == ""

    def test_reference_fields_always_none(self) -> None:
        rows = [(_make_posting(), _make_snapshot(), "bds")]
        corpus = rows_to_corpus(rows)
        assert corpus[0]["reference_pass1"] is None
        assert corpus[0]["reference_pass2"] is None
