"""Tests for Alembic migration chain integrity."""

import importlib.util
import pathlib
import types

import pytest

MIGRATION_CHAIN = [
    ("aa88b1c2d3e4", "f8a9b0c1d2e3"),
    ("bb47c2d3e4f5", "aa88b1c2d3e4"),
    ("cc45d3e4f5a6", "bb47c2d3e4f5"),
]

VERSIONS_DIR = pathlib.Path(__file__).parent.parent / "alembic" / "versions"


def _load_migration(revision: str) -> types.ModuleType:
    for f in VERSIONS_DIR.glob("*.py"):
        if revision in f.stem:
            spec = importlib.util.spec_from_file_location(f.stem, f)
            assert spec is not None and spec.loader is not None
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise FileNotFoundError(f"No migration found for revision {revision}")


@pytest.mark.parametrize("revision,expected_parent", MIGRATION_CHAIN)
def test_migration_chain(revision: str, expected_parent: str) -> None:
    mod = _load_migration(revision)
    assert mod.revision == revision
    assert mod.down_revision == expected_parent


def test_append_only_trigger_covers_fact_tables() -> None:
    mod = _load_migration("bb47c2d3e4f5")
    assert "posting_snapshots" in mod.FACT_TABLES
    assert "posting_enrichments" in mod.FACT_TABLES
    assert "posting_brand_mentions" in mod.FACT_TABLES
    assert "postings" not in mod.FACT_TABLES


def test_fk_indexes_cover_critical_columns() -> None:
    mod = _load_migration("cc45d3e4f5a6")
    index_specs = {(t, tuple(c)) for _, t, c in mod.FK_INDEXES}
    assert ("posting_enrichments", ("posting_id",)) in index_specs
    assert ("posting_brand_mentions", ("posting_id",)) in index_specs
