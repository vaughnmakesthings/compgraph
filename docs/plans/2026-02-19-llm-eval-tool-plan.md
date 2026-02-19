# CompGraph LLM Evaluation Tool — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a standalone Streamlit app that tests prompt/model combinations against CompGraph's enrichment pipeline with side-by-side human review and Elo ranking.

**Architecture:** Standalone `compgraph-eval/` project alongside CompGraph. SQLite for local storage, LiteLLM for multi-provider model switching, Streamlit for UI. Schemas copied from CompGraph (~60 lines). Prompts are versioned Python modules auto-discovered from `eval/prompts/`.

**Tech Stack:** Python 3.12+, uv, Streamlit, LiteLLM, aiosqlite, Pydantic 2.0

**Design doc:** `docs/plans/2026-02-19-llm-eval-tool-design.md`

---

## Task 1: Project Scaffolding

**Files:**
- Create: `compgraph-eval/pyproject.toml`
- Create: `compgraph-eval/.gitignore`
- Create: `compgraph-eval/.env.example`
- Create: `compgraph-eval/eval/__init__.py`
- Create: `compgraph-eval/eval/prompts/__init__.py`
- Create: `compgraph-eval/eval/ui/__init__.py`
- Create: `compgraph-eval/eval/ui/pages/__init__.py`
- Create: `compgraph-eval/data/.gitkeep`

**Step 1: Create project directory and pyproject.toml**

```bash
mkdir -p compgraph-eval
```

```toml
# compgraph-eval/pyproject.toml
[project]
name = "compgraph-eval"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "litellm>=1.50",
    "streamlit>=1.40",
    "aiosqlite>=0.20",
    "pydantic>=2.0",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
export = [
    "asyncpg>=0.29",
    "sqlalchemy[asyncio]>=2.0",
]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
]

[project.scripts]
eval-export = "scripts.export_corpus:main"
```

**Step 2: Create .gitignore**

```gitignore
# compgraph-eval/.gitignore
data/corpus.json
data/eval.db
.env
__pycache__/
*.pyc
.venv/
```

**Step 3: Create .env.example**

```bash
# compgraph-eval/.env.example
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
# GEMINI_API_KEY=...
# DEEPSEEK_API_KEY=...
```

**Step 4: Create package init files**

```bash
mkdir -p compgraph-eval/eval/prompts compgraph-eval/eval/ui/pages compgraph-eval/data compgraph-eval/scripts compgraph-eval/tests
touch compgraph-eval/eval/__init__.py
touch compgraph-eval/eval/ui/__init__.py
touch compgraph-eval/eval/ui/pages/__init__.py
touch compgraph-eval/data/.gitkeep
```

**Step 5: Initialize uv and install deps**

```bash
cd compgraph-eval && uv sync
```

**Step 6: Commit**

```bash
git init
git add .
git commit -m "chore: scaffold compgraph-eval project"
```

---

## Task 2: Schemas & Config

**Files:**
- Create: `compgraph-eval/eval/schemas.py`
- Create: `compgraph-eval/eval/config.py`
- Test: `compgraph-eval/tests/test_schemas.py`

**Step 1: Write the failing test**

```python
# compgraph-eval/tests/test_schemas.py
"""Tests for evaluation schemas and config."""

import pytest
from eval.schemas import Pass1Result, Pass2Result, EntityMention
from eval.config import MODELS


class TestPass1Result:
    def test_all_fields_optional(self):
        """Pass1Result should accept empty input (all fields null/default)."""
        result = Pass1Result()
        assert result.role_archetype is None
        assert result.pay_min is None
        assert result.tools_mentioned == []

    def test_full_result_parses(self):
        """Pass1Result should parse a complete JSON output."""
        data = {
            "role_archetype": "field_rep",
            "role_level": "entry",
            "employment_type": "full_time",
            "travel_required": True,
            "pay_type": "hourly",
            "pay_min": 18.0,
            "pay_max": 22.0,
            "pay_frequency": "hour",
            "has_commission": True,
            "has_benefits": True,
            "content_role_specific": "Visit 15 Best Buy stores weekly.",
            "content_boilerplate": "EEO statement.",
            "content_qualifications": "Must have valid driver's license.",
            "content_responsibilities": "Stock shelves, build displays.",
            "tools_mentioned": ["Salesforce", "Repsly"],
            "kpis_mentioned": ["store visits per day"],
            "store_count": 15,
        }
        result = Pass1Result(**data)
        assert result.role_archetype == "field_rep"
        assert result.pay_min == 18.0
        assert result.tools_mentioned == ["Salesforce", "Repsly"]
        assert result.store_count == 15

    def test_json_roundtrip(self):
        """Pass1Result should survive JSON serialization."""
        import json
        data = {"role_archetype": "merchandiser", "pay_min": 15.0, "tools_mentioned": ["Excel"]}
        result = Pass1Result(**data)
        json_str = result.model_dump_json()
        restored = Pass1Result.model_validate_json(json_str)
        assert restored.role_archetype == "merchandiser"
        assert restored.pay_min == 15.0


class TestPass2Result:
    def test_empty_entities(self):
        """Pass2Result should accept empty entities list."""
        result = Pass2Result()
        assert result.entities == []

    def test_entities_parse(self):
        """Pass2Result should parse entity mentions with confidence."""
        data = {
            "entities": [
                {"entity_name": "Samsung", "entity_type": "client_brand", "confidence": 0.95},
                {"entity_name": "Best Buy", "entity_type": "retailer", "confidence": 0.9},
            ]
        }
        result = Pass2Result(**data)
        assert len(result.entities) == 2
        assert result.entities[0].entity_name == "Samsung"
        assert result.entities[1].confidence == 0.9

    def test_confidence_bounds(self):
        """EntityMention should reject confidence outside 0-1."""
        with pytest.raises(Exception):
            EntityMention(entity_name="X", entity_type="client_brand", confidence=1.5)


class TestConfig:
    def test_models_dict_not_empty(self):
        """MODELS config should contain at least one model."""
        assert len(MODELS) > 0

    def test_models_have_string_values(self):
        """Each model alias should map to a LiteLLM model string."""
        for alias, model_id in MODELS.items():
            assert isinstance(alias, str)
            assert isinstance(model_id, str)
            assert len(model_id) > 0
```

**Step 2: Run test to verify it fails**

```bash
cd compgraph-eval && uv run pytest tests/test_schemas.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.schemas'`

**Step 3: Write schemas.py (copy from CompGraph)**

```python
# compgraph-eval/eval/schemas.py
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
```

**Step 4: Write config.py**

```python
# compgraph-eval/eval/config.py
"""Model configuration for LLM evaluation."""

MODELS: dict[str, str] = {
    "haiku-4.5": "claude-haiku-4-5-20251001",
    "sonnet-4.5": "claude-sonnet-4-5-20250929",
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-4o": "gpt-4o",
    "gemini-flash": "gemini/gemini-2.0-flash",
    "deepseek-v3": "deepseek/deepseek-chat",
}

DEFAULT_CONCURRENCY = 5
DEFAULT_MAX_TOKENS_PASS1 = 2048
DEFAULT_MAX_TOKENS_PASS2 = 1024
```

**Step 5: Run tests to verify they pass**

```bash
cd compgraph-eval && uv run pytest tests/test_schemas.py -v
```
Expected: All 8 tests PASS

**Step 6: Commit**

```bash
git add eval/schemas.py eval/config.py tests/test_schemas.py
git commit -m "feat: add schemas and model config"
```

---

## Task 3: SQLite Store

**Files:**
- Create: `compgraph-eval/eval/store.py`
- Test: `compgraph-eval/tests/test_store.py`

**Step 1: Write the failing test**

```python
# compgraph-eval/tests/test_store.py
"""Tests for SQLite store."""

import pytest
import pytest_asyncio
import asyncio
from pathlib import Path

from eval.store import EvalStore


@pytest_asyncio.fixture
async def store(tmp_path: Path):
    """Create a temporary store for testing."""
    db_path = tmp_path / "test.db"
    s = EvalStore(str(db_path))
    await s.init()
    yield s
    await s.close()


@pytest.mark.asyncio
async def test_init_creates_tables(store: EvalStore):
    """init() should create all 4 tables."""
    tables = await store.list_tables()
    assert "corpus" in tables
    assert "runs" in tables
    assert "results" in tables
    assert "comparisons" in tables


@pytest.mark.asyncio
async def test_insert_and_get_corpus(store: EvalStore):
    """Should insert and retrieve corpus postings."""
    posting = {
        "id": "abc-123",
        "company_slug": "bds",
        "title": "Field Rep",
        "location": "Atlanta, GA",
        "full_text": "Full job description here.",
    }
    await store.insert_corpus([posting])
    results = await store.get_corpus()
    assert len(results) == 1
    assert results[0]["id"] == "abc-123"
    assert results[0]["title"] == "Field Rep"


@pytest.mark.asyncio
async def test_create_and_get_run(store: EvalStore):
    """Should create a run and retrieve it."""
    run_id = await store.create_run(
        pass_number=1,
        model="haiku-4.5",
        prompt_version="pass1_v1",
        corpus_size=10,
    )
    assert run_id > 0
    run = await store.get_run(run_id)
    assert run["model"] == "haiku-4.5"
    assert run["corpus_size"] == 10


@pytest.mark.asyncio
async def test_insert_and_get_result(store: EvalStore):
    """Should insert a result and retrieve it by run."""
    await store.insert_corpus([{
        "id": "post-1", "company_slug": "bds",
        "title": "Rep", "location": "NY", "full_text": "Text",
    }])
    run_id = await store.create_run(1, "haiku-4.5", "pass1_v1", 1)
    await store.insert_result(
        run_id=run_id,
        posting_id="post-1",
        raw_response='{"role_archetype": "field_rep"}',
        parsed_result={"role_archetype": "field_rep"},
        parse_success=True,
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
        latency_ms=500,
    )
    results = await store.get_results(run_id)
    assert len(results) == 1
    assert results[0]["parse_success"] == 1
    assert results[0]["posting_id"] == "post-1"


@pytest.mark.asyncio
async def test_insert_comparison(store: EvalStore):
    """Should insert a comparison and retrieve comparisons for a run pair."""
    # Setup: corpus + 2 runs + 2 results
    await store.insert_corpus([{
        "id": "p1", "company_slug": "bds",
        "title": "Rep", "location": "NY", "full_text": "Text",
    }])
    run_a = await store.create_run(1, "haiku-4.5", "v1", 1)
    run_b = await store.create_run(1, "gpt-4o-mini", "v1", 1)
    await store.insert_result(run_a, "p1", "{}", {}, True, 100, 50, 0.001, 500)
    await store.insert_result(run_b, "p1", "{}", {}, True, 80, 40, 0.0005, 300)

    results_a = await store.get_results(run_a)
    results_b = await store.get_results(run_b)

    await store.insert_comparison(
        posting_id="p1",
        result_a_id=results_a[0]["id"],
        result_b_id=results_b[0]["id"],
        winner="a",
        notes="A extracted pay correctly",
    )
    comps = await store.get_comparisons()
    assert len(comps) == 1
    assert comps[0]["winner"] == "a"


@pytest.mark.asyncio
async def test_update_run_totals(store: EvalStore):
    """Should update run totals after results are collected."""
    run_id = await store.create_run(1, "haiku-4.5", "v1", 10)
    await store.update_run_totals(
        run_id,
        total_input_tokens=5000,
        total_output_tokens=2000,
        total_cost_usd=0.05,
        total_duration_ms=30000,
    )
    run = await store.get_run(run_id)
    assert run["total_input_tokens"] == 5000
    assert run["total_cost_usd"] == 0.05
```

**Step 2: Run tests to verify they fail**

```bash
cd compgraph-eval && uv run pytest tests/test_store.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.store'`

**Step 3: Write store.py**

```python
# compgraph-eval/eval/store.py
"""SQLite storage for evaluation runs, results, and comparisons."""

from __future__ import annotations

import json
import aiosqlite

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS corpus (
    id TEXT PRIMARY KEY,
    company_slug TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT,
    full_text TEXT NOT NULL,
    reference_pass1 JSON,
    reference_pass2 JSON
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    pass_number INTEGER NOT NULL CHECK (pass_number IN (1, 2)),
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    corpus_size INTEGER NOT NULL,
    total_input_tokens INTEGER,
    total_output_tokens INTEGER,
    total_cost_usd REAL,
    total_duration_ms INTEGER,
    UNIQUE(pass_number, model, prompt_version)
);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    posting_id TEXT NOT NULL REFERENCES corpus(id),
    raw_response TEXT,
    parsed_result JSON,
    parse_success BOOLEAN NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL,
    latency_ms INTEGER,
    UNIQUE(run_id, posting_id)
);

CREATE TABLE IF NOT EXISTS comparisons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    posting_id TEXT NOT NULL REFERENCES corpus(id),
    result_a_id INTEGER NOT NULL REFERENCES results(id),
    result_b_id INTEGER NOT NULL REFERENCES results(id),
    winner TEXT NOT NULL CHECK (winner IN ('a', 'b', 'tie', 'both_bad')),
    notes TEXT
);
"""


class EvalStore:
    """Async SQLite store for eval data."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA_SQL)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def list_tables(self) -> list[str]:
        cursor = await self._db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        rows = await cursor.fetchall()
        return [row["name"] for row in rows]

    # --- Corpus ---

    async def insert_corpus(self, postings: list[dict]) -> None:
        await self._db.executemany(
            """INSERT OR IGNORE INTO corpus (id, company_slug, title, location, full_text,
               reference_pass1, reference_pass2)
               VALUES (:id, :company_slug, :title, :location, :full_text,
               :reference_pass1, :reference_pass2)""",
            [
                {
                    "id": p["id"],
                    "company_slug": p["company_slug"],
                    "title": p["title"],
                    "location": p.get("location"),
                    "full_text": p["full_text"],
                    "reference_pass1": json.dumps(p.get("reference_pass1")),
                    "reference_pass2": json.dumps(p.get("reference_pass2")),
                }
                for p in postings
            ],
        )
        await self._db.commit()

    async def get_corpus(self) -> list[dict]:
        cursor = await self._db.execute("SELECT * FROM corpus")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # --- Runs ---

    async def create_run(
        self, pass_number: int, model: str, prompt_version: str, corpus_size: int
    ) -> int:
        cursor = await self._db.execute(
            """INSERT INTO runs (pass_number, model, prompt_version, corpus_size)
               VALUES (?, ?, ?, ?)""",
            (pass_number, model, prompt_version, corpus_size),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def get_run(self, run_id: int) -> dict:
        cursor = await self._db.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = await cursor.fetchone()
        return dict(row) if row else {}

    async def get_all_runs(self) -> list[dict]:
        cursor = await self._db.execute("SELECT * FROM runs ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def update_run_totals(
        self,
        run_id: int,
        total_input_tokens: int,
        total_output_tokens: int,
        total_cost_usd: float,
        total_duration_ms: int,
    ) -> None:
        await self._db.execute(
            """UPDATE runs SET total_input_tokens=?, total_output_tokens=?,
               total_cost_usd=?, total_duration_ms=? WHERE id=?""",
            (total_input_tokens, total_output_tokens, total_cost_usd, total_duration_ms, run_id),
        )
        await self._db.commit()

    async def delete_run(self, run_id: int) -> None:
        await self._db.execute("DELETE FROM results WHERE run_id = ?", (run_id,))
        await self._db.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        await self._db.commit()

    # --- Results ---

    async def insert_result(
        self,
        run_id: int,
        posting_id: str,
        raw_response: str,
        parsed_result: dict | None,
        parse_success: bool,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        latency_ms: int,
    ) -> int:
        cursor = await self._db.execute(
            """INSERT INTO results (run_id, posting_id, raw_response, parsed_result,
               parse_success, input_tokens, output_tokens, cost_usd, latency_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id, posting_id, raw_response,
                json.dumps(parsed_result) if parsed_result else None,
                parse_success, input_tokens, output_tokens, cost_usd, latency_ms,
            ),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def get_results(self, run_id: int) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM results WHERE run_id = ? ORDER BY posting_id", (run_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_result(self, result_id: int) -> dict:
        cursor = await self._db.execute("SELECT * FROM results WHERE id = ?", (result_id,))
        row = await cursor.fetchone()
        return dict(row) if row else {}

    # --- Comparisons ---

    async def insert_comparison(
        self,
        posting_id: str,
        result_a_id: int,
        result_b_id: int,
        winner: str,
        notes: str | None = None,
    ) -> int:
        cursor = await self._db.execute(
            """INSERT INTO comparisons (posting_id, result_a_id, result_b_id, winner, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (posting_id, result_a_id, result_b_id, winner, notes),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def get_comparisons(self) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM comparisons ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
```

**Step 4: Run tests to verify they pass**

```bash
cd compgraph-eval && uv run pytest tests/test_store.py -v
```
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add eval/store.py tests/test_store.py
git commit -m "feat: add SQLite store with CRUD for runs, results, comparisons"
```

---

## Task 4: Prompt Registry

**Files:**
- Create: `compgraph-eval/eval/prompts/__init__.py` (replace empty init)
- Create: `compgraph-eval/eval/prompts/pass1_v1.py`
- Create: `compgraph-eval/eval/prompts/pass2_v1.py`
- Test: `compgraph-eval/tests/test_prompts.py`

**Step 1: Write the failing test**

```python
# compgraph-eval/tests/test_prompts.py
"""Tests for prompt registry."""

import pytest
from eval.prompts import list_prompts, load_prompt


class TestPromptRegistry:
    def test_list_pass1_prompts(self):
        """Should discover pass1_v1 prompt."""
        prompts = list_prompts(pass_number=1)
        assert "pass1_v1" in prompts

    def test_list_pass2_prompts(self):
        """Should discover pass2_v1 prompt."""
        prompts = list_prompts(pass_number=2)
        assert "pass2_v1" in prompts

    def test_load_pass1_prompt(self):
        """Should load system prompt and build function."""
        system_prompt, build_fn = load_prompt("pass1_v1")
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 100
        assert callable(build_fn)

    def test_build_pass1_message(self):
        """build_user_message should format posting into XML tags."""
        _, build_fn = load_prompt("pass1_v1")
        msg = build_fn(title="Field Rep", location="Atlanta, GA", full_text="Job description.")
        assert "<title>Field Rep</title>" in msg
        assert "<location>Atlanta, GA</location>" in msg
        assert "Job description." in msg

    def test_load_pass2_prompt(self):
        """Should load pass2 system prompt and build function."""
        system_prompt, build_fn = load_prompt("pass2_v1")
        assert "entity" in system_prompt.lower()
        assert callable(build_fn)

    def test_build_pass2_message(self):
        """Pass 2 build function takes content_role_specific as extra param."""
        _, build_fn = load_prompt("pass2_v1")
        msg = build_fn(
            title="Field Rep",
            location="Atlanta, GA",
            full_text="Full text here.",
            content_role_specific="Visit Best Buy stores.",
        )
        # Should use content_role_specific as body, not full_text
        assert "Visit Best Buy stores." in msg

    def test_load_nonexistent_prompt_raises(self):
        """Should raise ImportError for unknown prompt version."""
        with pytest.raises(ImportError):
            load_prompt("pass1_v999")
```

**Step 2: Run test to verify it fails**

```bash
cd compgraph-eval && uv run pytest tests/test_prompts.py -v
```
Expected: FAIL — `ImportError: cannot import name 'list_prompts'`

**Step 3: Write prompt registry __init__.py**

```python
# compgraph-eval/eval/prompts/__init__.py
"""Auto-discovering prompt registry.

Scans this directory for pass{N}_*.py files. Each module must export:
- SYSTEM_PROMPT: str
- build_user_message: Callable[..., str]
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Callable


def list_prompts(pass_number: int) -> list[str]:
    """Return available prompt version names for a given pass."""
    prompts_dir = Path(__file__).parent
    prefix = f"pass{pass_number}_"
    return sorted(
        p.stem
        for p in prompts_dir.glob(f"{prefix}*.py")
        if not p.name.startswith("_")
    )


def load_prompt(version: str) -> tuple[str, Callable]:
    """Load a prompt module by version name.

    Returns (SYSTEM_PROMPT, build_user_message) tuple.
    Raises ImportError if the module doesn't exist.
    """
    mod = importlib.import_module(f"eval.prompts.{version}")
    return mod.SYSTEM_PROMPT, mod.build_user_message
```

**Step 4: Write pass1_v1.py (copied from CompGraph production)**

Copy the full `PASS1_SYSTEM_PROMPT` from `src/compgraph/enrichment/prompts.py` (lines 5-94) and the `build_pass1_user_message` function (lines 97-106). Rename the function to `build_user_message`.

```python
# compgraph-eval/eval/prompts/pass1_v1.py
"""Pass 1 prompt — Production baseline.

Copied from compgraph/enrichment/prompts.py on 2026-02-19.
"""

SYSTEM_PROMPT = """\
You are a field marketing job posting analyst. You extract structured data from job postings \
published by field marketing agencies (companies that deploy sales reps, merchandisers, and \
brand ambassadors into retail stores on behalf of consumer brands).

<task>
Analyze the provided job posting and extract the following structured information. \
Return a JSON object with these fields. Use null for any field you cannot determine.
</task>

<fields>
...FULL PROMPT TEXT FROM compgraph/enrichment/prompts.py PASS1_SYSTEM_PROMPT...
</fields>

<rules>
...
</rules>

<examples>
...
</examples>"""


def build_user_message(title: str, location: str, full_text: str, **kwargs) -> str:
    """Format posting into XML tags for the LLM."""
    return f"""\
<posting>
<title>{title}</title>
<location>{location}</location>
<body>
{full_text}
</body>
</posting>"""
```

**Note to implementer:** Copy the FULL prompt text verbatim from `src/compgraph/enrichment/prompts.py` lines 5-94. Do not abbreviate.

**Step 5: Write pass2_v1.py (copied from CompGraph production)**

Copy `PASS2_SYSTEM_PROMPT` (lines 127-195) and adapt `build_pass2_user_message` (lines 198-217).

```python
# compgraph-eval/eval/prompts/pass2_v1.py
"""Pass 2 prompt — Production baseline.

Copied from compgraph/enrichment/prompts.py on 2026-02-19.
"""

SYSTEM_PROMPT = """\
You are a field marketing entity extraction specialist. ...
...FULL PROMPT TEXT FROM compgraph/enrichment/prompts.py PASS2_SYSTEM_PROMPT..."""


def build_user_message(
    title: str,
    location: str,
    full_text: str,
    content_role_specific: str | None = None,
    **kwargs,
) -> str:
    """Format posting for Pass 2. Prefers content_role_specific if available."""
    primary_content = content_role_specific or full_text
    return f"""\
<posting>
<title>{title}</title>
<location>{location}</location>
<body>
{primary_content}
</body>
</posting>"""
```

**Note to implementer:** Copy the FULL prompt text verbatim from `src/compgraph/enrichment/prompts.py` lines 127-195. Do not abbreviate.

**Step 6: Run tests to verify they pass**

```bash
cd compgraph-eval && uv run pytest tests/test_prompts.py -v
```
Expected: All 7 tests PASS

**Step 7: Commit**

```bash
git add eval/prompts/ tests/test_prompts.py
git commit -m "feat: add prompt registry with production baseline prompts"
```

---

## Task 5: LLM Provider Wrapper

**Files:**
- Create: `compgraph-eval/eval/providers.py`
- Test: `compgraph-eval/tests/test_providers.py`

**Step 1: Write the failing test**

```python
# compgraph-eval/tests/test_providers.py
"""Tests for LLM provider wrapper."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from eval.providers import call_llm, LLMResponse


class TestLLMResponse:
    def test_response_dataclass(self):
        """LLMResponse should store all fields."""
        resp = LLMResponse(
            content='{"role_archetype": "field_rep"}',
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            latency_ms=500,
        )
        assert resp.content == '{"role_archetype": "field_rep"}'
        assert resp.cost_usd == 0.001


class TestCallLLM:
    @pytest.mark.asyncio
    async def test_call_returns_response(self):
        """call_llm should return LLMResponse with content and metrics."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"role_archetype": "field_rep"}'
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response._hidden_params = {"response_cost": 0.001}

        with patch("eval.providers.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await call_llm(
                model="haiku-4.5",
                system_prompt="You are a test.",
                user_message="Hello.",
                max_tokens=1024,
            )
            assert result.content == '{"role_archetype": "field_rep"}'
            assert result.input_tokens == 100
            assert result.output_tokens == 50
            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_passes_model_string(self):
        """call_llm should resolve model alias to LiteLLM model string."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "{}"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response._hidden_params = {"response_cost": 0.0}

        with patch("eval.providers.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            await call_llm("haiku-4.5", "sys", "user", 1024)
            call_kwargs = mock_llm.call_args
            assert call_kwargs.kwargs["model"] == "claude-haiku-4-5-20251001"
```

**Step 2: Run test to verify it fails**

```bash
cd compgraph-eval && uv run pytest tests/test_providers.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.providers'`

**Step 3: Write providers.py**

```python
# compgraph-eval/eval/providers.py
"""LLM provider wrapper using LiteLLM."""

from __future__ import annotations

import time
from dataclasses import dataclass

import litellm
from eval.config import MODELS

# Suppress LiteLLM's verbose logging
litellm.suppress_debug_info = True


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    content: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int


async def call_llm(
    model: str,
    system_prompt: str,
    user_message: str,
    max_tokens: int,
) -> LLMResponse:
    """Call an LLM via LiteLLM and return standardized response.

    Args:
        model: Model alias from config.MODELS (e.g. "haiku-4.5")
        system_prompt: System prompt text
        user_message: User message text
        max_tokens: Max output tokens
    """
    model_id = MODELS[model]
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    start = time.perf_counter()
    response = await litellm.acompletion(
        model=model_id,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.1,
    )
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    content = response.choices[0].message.content or ""
    cost = response._hidden_params.get("response_cost", 0.0) or 0.0

    return LLMResponse(
        content=content,
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
        cost_usd=cost,
        latency_ms=elapsed_ms,
    )
```

**Step 4: Run tests to verify they pass**

```bash
cd compgraph-eval && uv run pytest tests/test_providers.py -v
```
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add eval/providers.py tests/test_providers.py
git commit -m "feat: add LiteLLM provider wrapper with cost tracking"
```

---

## Task 6: Runner (Test Execution Engine)

**Files:**
- Create: `compgraph-eval/eval/runner.py`
- Test: `compgraph-eval/tests/test_runner.py`

**Step 1: Write the failing test**

```python
# compgraph-eval/tests/test_runner.py
"""Tests for evaluation runner."""

import json
import pytest
import pytest_asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

from eval.runner import run_evaluation, load_corpus, RunSummary
from eval.store import EvalStore
from eval.providers import LLMResponse


@pytest_asyncio.fixture
async def store(tmp_path: Path):
    s = EvalStore(str(tmp_path / "test.db"))
    await s.init()
    yield s
    await s.close()


@pytest.fixture
def corpus_file(tmp_path: Path) -> Path:
    """Create a minimal corpus JSON file."""
    postings = [
        {
            "id": "post-1",
            "company_slug": "bds",
            "title": "Field Rep - Samsung",
            "location": "Atlanta, GA",
            "full_text": "Visit Best Buy stores weekly. $18-22/hr. Commission available.",
        },
        {
            "id": "post-2",
            "company_slug": "troc",
            "title": "Merchandiser",
            "location": "Dallas, TX",
            "full_text": "Stock shelves at Target locations. Part-time.",
        },
    ]
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(postings))
    return path


def test_load_corpus(corpus_file: Path):
    """Should load postings from JSON file."""
    postings = load_corpus(str(corpus_file))
    assert len(postings) == 2
    assert postings[0]["id"] == "post-1"


@pytest.mark.asyncio
async def test_run_evaluation_stores_results(store: EvalStore, corpus_file: Path):
    """Runner should create a run, call LLM for each posting, store results."""
    mock_response = LLMResponse(
        content='{"role_archetype": "field_rep", "pay_min": 18.0}',
        input_tokens=500,
        output_tokens=100,
        cost_usd=0.002,
        latency_ms=800,
    )

    with patch("eval.runner.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response
        summary = await run_evaluation(
            store=store,
            pass_number=1,
            model="haiku-4.5",
            prompt_version="pass1_v1",
            corpus_path=str(corpus_file),
            concurrency=2,
        )

    assert summary.total == 2
    assert summary.succeeded == 2
    assert summary.failed == 0
    assert mock_llm.call_count == 2

    # Verify stored in DB
    runs = await store.get_all_runs()
    assert len(runs) == 1
    assert runs[0]["model"] == "haiku-4.5"

    results = await store.get_results(runs[0]["id"])
    assert len(results) == 2
    assert all(r["parse_success"] for r in results)


@pytest.mark.asyncio
async def test_run_handles_parse_failure(store: EvalStore, corpus_file: Path):
    """Runner should store parse failures without crashing."""
    mock_response = LLMResponse(
        content="This is not valid JSON at all",
        input_tokens=500,
        output_tokens=100,
        cost_usd=0.002,
        latency_ms=800,
    )

    with patch("eval.runner.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response
        summary = await run_evaluation(
            store=store,
            pass_number=1,
            model="haiku-4.5",
            prompt_version="pass1_v1",
            corpus_path=str(corpus_file),
            concurrency=2,
        )

    assert summary.total == 2
    assert summary.succeeded == 0
    assert summary.failed == 2

    results = await store.get_results(1)
    assert all(not r["parse_success"] for r in results)
    # Raw response should still be stored for debugging
    assert all(r["raw_response"] is not None for r in results)
```

**Step 2: Run test to verify it fails**

```bash
cd compgraph-eval && uv run pytest tests/test_runner.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.runner'`

**Step 3: Write runner.py**

```python
# compgraph-eval/eval/runner.py
"""Evaluation runner — executes prompt×model combos against a corpus."""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from eval.config import DEFAULT_MAX_TOKENS_PASS1, DEFAULT_MAX_TOKENS_PASS2
from eval.prompts import load_prompt
from eval.providers import call_llm
from eval.schemas import Pass1Result, Pass2Result
from eval.store import EvalStore


@dataclass
class RunSummary:
    """Summary of an evaluation run."""

    run_id: int = 0
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    total_cost_usd: float = 0.0
    total_duration_ms: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0


def load_corpus(corpus_path: str) -> list[dict]:
    """Load corpus postings from a JSON file."""
    return json.loads(Path(corpus_path).read_text())


def strip_markdown_fences(text: str) -> str:
    """Strip markdown code fences from LLM response."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def parse_result(raw: str, pass_number: int) -> dict | None:
    """Parse raw LLM response into validated Pydantic model, return dict or None."""
    try:
        cleaned = strip_markdown_fences(raw)
        data = json.loads(cleaned)
        if pass_number == 1:
            result = Pass1Result(**data)
        else:
            result = Pass2Result(**data)
        return result.model_dump()
    except Exception:
        return None


async def _process_posting(
    posting: dict,
    model: str,
    system_prompt: str,
    build_fn,
    pass_number: int,
    max_tokens: int,
    store: EvalStore,
    run_id: int,
    semaphore: asyncio.Semaphore,
) -> tuple[bool, int, int, float, int]:
    """Process a single posting. Returns (success, in_tok, out_tok, cost, latency)."""
    async with semaphore:
        build_kwargs = {
            "title": posting["title"],
            "location": posting.get("location", ""),
            "full_text": posting["full_text"],
        }
        # Pass 2 may use content_role_specific
        if pass_number == 2 and posting.get("content_role_specific"):
            build_kwargs["content_role_specific"] = posting["content_role_specific"]

        user_message = build_fn(**build_kwargs)

        response = await call_llm(
            model=model,
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=max_tokens,
        )

        parsed = parse_result(response.content, pass_number)

        await store.insert_result(
            run_id=run_id,
            posting_id=posting["id"],
            raw_response=response.content,
            parsed_result=parsed,
            parse_success=parsed is not None,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
        )

        return (
            parsed is not None,
            response.input_tokens,
            response.output_tokens,
            response.cost_usd,
            response.latency_ms,
        )


async def run_evaluation(
    store: EvalStore,
    pass_number: int,
    model: str,
    prompt_version: str,
    corpus_path: str,
    concurrency: int = 5,
    on_progress: callable | None = None,
) -> RunSummary:
    """Run an evaluation: load corpus, call LLM for each posting, store results.

    Args:
        store: EvalStore instance
        pass_number: 1 or 2
        model: Model alias from config.MODELS
        prompt_version: Prompt module name (e.g. "pass1_v1")
        corpus_path: Path to corpus.json
        concurrency: Max parallel LLM calls
        on_progress: Optional callback(completed, total) for UI progress
    """
    postings = load_corpus(corpus_path)
    system_prompt, build_fn = load_prompt(prompt_version)
    max_tokens = DEFAULT_MAX_TOKENS_PASS1 if pass_number == 1 else DEFAULT_MAX_TOKENS_PASS2

    # Load corpus into store if not already there
    await store.insert_corpus(postings)

    run_id = await store.create_run(pass_number, model, prompt_version, len(postings))

    semaphore = asyncio.Semaphore(concurrency)
    summary = RunSummary(run_id=run_id, total=len(postings))

    start = time.perf_counter()

    tasks = [
        _process_posting(
            posting, model, system_prompt, build_fn,
            pass_number, max_tokens, store, run_id, semaphore,
        )
        for posting in postings
    ]

    for coro in asyncio.as_completed(tasks):
        success, in_tok, out_tok, cost, latency = await coro
        if success:
            summary.succeeded += 1
        else:
            summary.failed += 1
        summary.total_input_tokens += in_tok
        summary.total_output_tokens += out_tok
        summary.total_cost_usd += cost
        if on_progress:
            on_progress(summary.succeeded + summary.failed, summary.total)

    summary.total_duration_ms = int((time.perf_counter() - start) * 1000)

    await store.update_run_totals(
        run_id,
        summary.total_input_tokens,
        summary.total_output_tokens,
        summary.total_cost_usd,
        summary.total_duration_ms,
    )

    return summary
```

**Step 4: Run tests to verify they pass**

```bash
cd compgraph-eval && uv run pytest tests/test_runner.py -v
```
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add eval/runner.py tests/test_runner.py
git commit -m "feat: add evaluation runner with concurrent LLM execution"
```

---

## Task 7: Elo Rating Calculator

**Files:**
- Create: `compgraph-eval/eval/elo.py`
- Test: `compgraph-eval/tests/test_elo.py`

**Step 1: Write the failing test**

```python
# compgraph-eval/tests/test_elo.py
"""Tests for Elo rating calculator."""

from eval.elo import calculate_elo_ratings


def test_single_comparison_winner_gains():
    """Winner should gain points, loser should lose."""
    comparisons = [
        {"result_a_id": 1, "result_b_id": 2, "winner": "a"},
    ]
    run_map = {1: "haiku/v1", 2: "gpt4o-mini/v1"}
    ratings = calculate_elo_ratings(comparisons, run_map)
    assert ratings["haiku/v1"] > 1500
    assert ratings["gpt4o-mini/v1"] < 1500


def test_tie_no_change():
    """A tie should result in minimal rating change."""
    comparisons = [
        {"result_a_id": 1, "result_b_id": 2, "winner": "tie"},
    ]
    run_map = {1: "haiku/v1", 2: "gpt4o-mini/v1"}
    ratings = calculate_elo_ratings(comparisons, run_map)
    # Both should stay near 1500
    assert abs(ratings["haiku/v1"] - 1500) < 1
    assert abs(ratings["gpt4o-mini/v1"] - 1500) < 1


def test_both_bad_no_change():
    """both_bad should not affect ratings."""
    comparisons = [
        {"result_a_id": 1, "result_b_id": 2, "winner": "both_bad"},
    ]
    run_map = {1: "haiku/v1", 2: "gpt4o-mini/v1"}
    ratings = calculate_elo_ratings(comparisons, run_map)
    assert ratings["haiku/v1"] == 1500
    assert ratings["gpt4o-mini/v1"] == 1500


def test_multiple_comparisons():
    """Multiple wins should compound rating advantage."""
    comparisons = [
        {"result_a_id": 1, "result_b_id": 2, "winner": "a"},
        {"result_a_id": 1, "result_b_id": 2, "winner": "a"},
        {"result_a_id": 1, "result_b_id": 2, "winner": "a"},
    ]
    run_map = {1: "haiku/v1", 2: "gpt4o-mini/v1"}
    ratings = calculate_elo_ratings(comparisons, run_map)
    assert ratings["haiku/v1"] > ratings["gpt4o-mini/v1"]
    assert ratings["haiku/v1"] > 1530  # Significant lead after 3 wins
```

**Step 2: Run test to verify it fails**

```bash
cd compgraph-eval && uv run pytest tests/test_elo.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.elo'`

**Step 3: Write elo.py**

```python
# compgraph-eval/eval/elo.py
"""Elo rating calculator for LLM comparison results."""

from __future__ import annotations

DEFAULT_K = 32
DEFAULT_RATING = 1500


def calculate_elo_ratings(
    comparisons: list[dict],
    run_map: dict[int, str],
    k: int = DEFAULT_K,
) -> dict[str, float]:
    """Calculate Elo ratings from comparison results.

    Args:
        comparisons: List of comparison dicts with result_a_id, result_b_id, winner
        run_map: Maps result_id → "model/prompt_version" label
        k: Elo K-factor (higher = more volatile)

    Returns:
        Dict mapping "model/prompt_version" → Elo rating
    """
    ratings: dict[str, float] = {}

    # Initialize all players
    for label in run_map.values():
        ratings.setdefault(label, DEFAULT_RATING)

    for comp in comparisons:
        a_id = comp["result_a_id"]
        b_id = comp["result_b_id"]
        winner = comp["winner"]

        if winner == "both_bad":
            continue

        label_a = run_map.get(a_id)
        label_b = run_map.get(b_id)
        if not label_a or not label_b or label_a == label_b:
            continue

        ra = ratings[label_a]
        rb = ratings[label_b]

        # Expected scores
        ea = 1.0 / (1.0 + 10 ** ((rb - ra) / 400))
        eb = 1.0 - ea

        # Actual scores
        if winner == "a":
            sa, sb = 1.0, 0.0
        elif winner == "b":
            sa, sb = 0.0, 1.0
        else:  # tie
            sa, sb = 0.5, 0.5

        ratings[label_a] = ra + k * (sa - ea)
        ratings[label_b] = rb + k * (sb - eb)

    return ratings
```

**Step 4: Run tests to verify they pass**

```bash
cd compgraph-eval && uv run pytest tests/test_elo.py -v
```
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add eval/elo.py tests/test_elo.py
git commit -m "feat: add Elo rating calculator"
```

---

## Task 8: Corpus Export Script

**Files:**
- Create: `compgraph-eval/scripts/export_corpus.py`

This is a utility script, not tested via pytest (requires live Supabase connection).

**Step 1: Write export_corpus.py**

```python
# compgraph-eval/scripts/export_corpus.py
"""Export postings from CompGraph Supabase DB to local corpus.json.

Usage:
    cd compgraph-eval
    op run --env-file=../.env -- uv run python scripts/export_corpus.py --limit 100

Requires [export] optional dependencies: asyncpg, sqlalchemy[asyncio]
"""

from __future__ import annotations

import asyncio
import json
import argparse
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text


async def export(database_url: str, output_path: str, limit: int) -> None:
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        query = text("""
            SELECT
                p.id::text as id,
                c.slug as company_slug,
                p.title,
                p.location,
                p.full_text_raw as full_text,
                jsonb_build_object(
                    'role_archetype', pe.role_archetype,
                    'role_level', pe.role_level,
                    'employment_type', pe.employment_type,
                    'pay_type', pe.pay_type,
                    'pay_min', pe.pay_min,
                    'pay_max', pe.pay_max,
                    'pay_frequency', pe.pay_frequency,
                    'has_commission', pe.has_commission,
                    'has_benefits', pe.has_benefits,
                    'content_role_specific', pe.content_role_specific
                ) as reference_pass1
            FROM postings p
            JOIN companies c ON p.company_id = c.id
            LEFT JOIN posting_enrichments pe ON p.id = pe.posting_id
            WHERE p.full_text_raw IS NOT NULL
              AND length(p.full_text_raw) > 100
            ORDER BY random()
            LIMIT :limit
        """)
        result = await session.execute(query, {"limit": limit})
        rows = result.mappings().all()

    postings = []
    for row in rows:
        posting = {
            "id": row["id"],
            "company_slug": row["company_slug"],
            "title": row["title"],
            "location": row["location"],
            "full_text": row["full_text"],
            "reference_pass1": dict(row["reference_pass1"]) if row["reference_pass1"] else None,
        }
        postings.append(posting)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(postings, indent=2))
    print(f"Exported {len(postings)} postings to {output_path}")

    await engine.dispose()


def main():
    import os
    parser = argparse.ArgumentParser(description="Export postings to corpus.json")
    parser.add_argument("--limit", type=int, default=100, help="Number of postings")
    parser.add_argument("--output", default="data/corpus.json", help="Output path")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set. Use: op run --env-file=../.env --")
        raise SystemExit(1)

    asyncio.run(export(database_url, args.output, args.limit))


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add scripts/export_corpus.py
git commit -m "feat: add corpus export script for Supabase"
```

---

## Task 9: Streamlit UI — Page 1 (Run Tests)

**Files:**
- Create: `compgraph-eval/eval/ui/app.py`
- Create: `compgraph-eval/eval/ui/pages/1_Run_Tests.py`

**Step 1: Write app.py (Streamlit entry point)**

```python
# compgraph-eval/eval/ui/app.py
"""CompGraph LLM Eval — Streamlit entry point."""

import streamlit as st

st.set_page_config(
    page_title="CompGraph LLM Eval",
    page_icon="🔬",
    layout="wide",
)

st.title("CompGraph LLM Eval")
st.markdown(
    "Test prompt/model combinations against the enrichment pipeline. "
    "Navigate using the sidebar."
)
```

**Step 2: Write Page 1 — Run Tests**

```python
# compgraph-eval/eval/ui/pages/1_Run_Tests.py
"""Page 1: Run evaluation tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

import streamlit as st

from eval.config import MODELS
from eval.prompts import list_prompts
from eval.runner import run_evaluation
from eval.store import EvalStore

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
DB_PATH = str(DATA_DIR / "eval.db")
CORPUS_PATH = str(DATA_DIR / "corpus.json")


@st.cache_resource
def get_store() -> EvalStore:
    store = EvalStore(DB_PATH)
    asyncio.get_event_loop().run_until_complete(store.init())
    return store


st.header("Run Evaluation")

# --- Check corpus exists ---
if not Path(CORPUS_PATH).exists():
    st.error(
        "No corpus found at `data/corpus.json`. "
        "Run `scripts/export_corpus.py` first."
    )
    st.stop()

store = get_store()

# --- Run form ---
col1, col2, col3 = st.columns(3)

with col1:
    pass_number = st.selectbox("Pass", [1, 2])

with col2:
    model = st.selectbox("Model", list(MODELS.keys()))

with col3:
    prompt_versions = list_prompts(pass_number)
    prompt_version = st.selectbox("Prompt Version", prompt_versions)

concurrency = st.slider("Concurrency", min_value=1, max_value=20, value=5)

if st.button("Run Evaluation", type="primary"):
    progress_bar = st.progress(0)
    status = st.empty()

    def on_progress(completed: int, total: int):
        progress_bar.progress(completed / total)
        status.text(f"Processing {completed}/{total} postings...")

    with st.spinner("Running evaluation..."):
        summary = asyncio.get_event_loop().run_until_complete(
            run_evaluation(
                store=store,
                pass_number=pass_number,
                model=model,
                prompt_version=prompt_version,
                corpus_path=CORPUS_PATH,
                concurrency=concurrency,
                on_progress=on_progress,
            )
        )

    progress_bar.progress(1.0)
    st.success(
        f"Done! {summary.succeeded}/{summary.total} succeeded, "
        f"${summary.total_cost_usd:.4f} total cost, "
        f"{summary.total_duration_ms/1000:.1f}s"
    )

# --- Run history ---
st.subheader("Run History")

runs = asyncio.get_event_loop().run_until_complete(store.get_all_runs())
if runs:
    import pandas as pd

    df = pd.DataFrame(runs)
    # Compute success rate from results
    for i, run in enumerate(runs):
        results = asyncio.get_event_loop().run_until_complete(
            store.get_results(run["id"])
        )
        total = len(results)
        success = sum(1 for r in results if r["parse_success"])
        df.loc[i, "success_rate"] = f"{success}/{total}" if total > 0 else "—"

    display_cols = [
        "id", "pass_number", "model", "prompt_version",
        "success_rate", "total_cost_usd", "total_duration_ms",
    ]
    st.dataframe(
        df[[c for c in display_cols if c in df.columns]],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No runs yet. Run your first evaluation above.")
```

**Step 3: Verify it launches**

```bash
cd compgraph-eval && uv run streamlit run eval/ui/app.py
```
Expected: Browser opens, sidebar shows "Run Tests" page, form renders.

**Step 4: Commit**

```bash
git add eval/ui/app.py eval/ui/pages/1_Run_Tests.py
git commit -m "feat: add Streamlit Run Tests page"
```

---

## Task 10: Streamlit UI — Page 2 (Side-by-Side Review)

**Files:**
- Create: `compgraph-eval/eval/ui/pages/2_Review.py`
- Create: `compgraph-eval/eval/ui/components.py`

**Step 1: Write components.py (diff highlighting helper)**

```python
# compgraph-eval/eval/ui/components.py
"""Shared UI components for the eval tool."""

from __future__ import annotations

import json
import streamlit as st


def render_pass1_diff(result_a: dict | None, result_b: dict | None) -> None:
    """Render two Pass 1 results side-by-side with diff highlighting."""
    if not result_a and not result_b:
        st.warning("Both results failed to parse.")
        return

    a = result_a or {}
    b = result_b or {}

    fields = [
        "role_archetype", "role_level", "employment_type", "travel_required",
        "pay_type", "pay_min", "pay_max", "pay_frequency",
        "has_commission", "has_benefits",
        "tools_mentioned", "kpis_mentioned", "store_count",
    ]

    col_a, col_b = st.columns(2)

    for field in fields:
        val_a = a.get(field)
        val_b = b.get(field)
        differs = val_a != val_b
        marker = " ⚠️" if differs else ""

        with col_a:
            st.text(f"{field}: {_fmt(val_a)}{marker}")
        with col_b:
            st.text(f"{field}: {_fmt(val_b)}{marker}")


def render_pass2_diff(result_a: dict | None, result_b: dict | None) -> None:
    """Render two Pass 2 results side-by-side."""
    a_entities = (result_a or {}).get("entities", [])
    b_entities = (result_b or {}).get("entities", [])

    col_a, col_b = st.columns(2)

    with col_a:
        if a_entities:
            for e in a_entities:
                st.text(f"  {e['entity_name']} ({e['entity_type']}) — {e['confidence']:.2f}")
        else:
            st.text("  (no entities)")

    with col_b:
        if b_entities:
            for e in b_entities:
                st.text(f"  {e['entity_name']} ({e['entity_type']}) — {e['confidence']:.2f}")
        else:
            st.text("  (no entities)")


def _fmt(val) -> str:
    """Format a value for display."""
    if val is None:
        return "null"
    if isinstance(val, list):
        return json.dumps(val) if val else "[]"
    return str(val)
```

**Step 2: Write Page 2 — Review**

```python
# compgraph-eval/eval/ui/pages/2_Review.py
"""Page 2: Side-by-side review with Elo voting."""

from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path

import streamlit as st

from eval.store import EvalStore
from eval.ui.components import render_pass1_diff, render_pass2_diff

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
DB_PATH = str(DATA_DIR / "eval.db")


@st.cache_resource
def get_store() -> EvalStore:
    store = EvalStore(DB_PATH)
    asyncio.get_event_loop().run_until_complete(store.init())
    return store


store = get_store()
st.header("Side-by-Side Review")

# --- Select two runs to compare ---
runs = asyncio.get_event_loop().run_until_complete(store.get_all_runs())
if len(runs) < 2:
    st.info("Need at least 2 completed runs to compare. Go to Run Tests first.")
    st.stop()

run_labels = {r["id"]: f"#{r['id']} {r['model']}/{r['prompt_version']} (Pass {r['pass_number']})" for r in runs}

col1, col2 = st.columns(2)
with col1:
    run_a_id = st.selectbox("Run A", list(run_labels.keys()), format_func=lambda x: run_labels[x])
with col2:
    run_b_id = st.selectbox("Run B", list(run_labels.keys()), index=min(1, len(runs)-1), format_func=lambda x: run_labels[x])

if run_a_id == run_b_id:
    st.warning("Select two different runs to compare.")
    st.stop()

# --- Load results for both runs ---
results_a = asyncio.get_event_loop().run_until_complete(store.get_results(run_a_id))
results_b = asyncio.get_event_loop().run_until_complete(store.get_results(run_b_id))

# Build lookup by posting_id
a_by_posting = {r["posting_id"]: r for r in results_a}
b_by_posting = {r["posting_id"]: r for r in results_b}

# Find common postings (both runs evaluated)
common_ids = sorted(set(a_by_posting.keys()) & set(b_by_posting.keys()))
if not common_ids:
    st.warning("No overlapping postings between these runs.")
    st.stop()

# --- Navigation ---
if "review_idx" not in st.session_state:
    st.session_state.review_idx = 0
    # Randomize A/B assignment per posting for this session
    st.session_state.swap_map = {pid: random.random() > 0.5 for pid in common_ids}

idx = st.session_state.review_idx
posting_id = common_ids[idx]

st.progress((idx + 1) / len(common_ids))
st.caption(f"Comparison {idx + 1} of {len(common_ids)}")

# --- Load posting text ---
corpus = asyncio.get_event_loop().run_until_complete(store.get_corpus())
posting = next((p for p in corpus if p["id"] == posting_id), None)

if posting:
    st.subheader(f"{posting['title']}")
    st.caption(f"{posting.get('company_slug', '')} | {posting.get('location', '')}")
    with st.expander("Full posting text"):
        st.text(posting["full_text"][:2000])

# --- Determine A/B assignment (randomized) ---
swapped = st.session_state.swap_map.get(posting_id, False)
if swapped:
    left_result, right_result = b_by_posting[posting_id], a_by_posting[posting_id]
    left_run, right_run = run_labels[run_b_id], run_labels[run_a_id]
    left_id, right_id = "b", "a"
else:
    left_result, right_result = a_by_posting[posting_id], b_by_posting[posting_id]
    left_run, right_run = run_labels[run_a_id], run_labels[run_b_id]
    left_id, right_id = "a", "b"

# --- Display results ---
col_left, col_right = st.columns(2)
with col_left:
    st.markdown(f"**Option A** — `{left_run}`")
with col_right:
    st.markdown(f"**Option B** — `{right_run}`")

# Determine pass number from the run
run_a_data = next(r for r in runs if r["id"] == run_a_id)
pass_number = run_a_data["pass_number"]

parsed_left = json.loads(left_result["parsed_result"]) if left_result.get("parsed_result") else None
parsed_right = json.loads(right_result["parsed_result"]) if right_result.get("parsed_result") else None

if pass_number == 1:
    render_pass1_diff(parsed_left, parsed_right)
else:
    render_pass2_diff(parsed_left, parsed_right)

# --- Voting ---
st.divider()
notes = st.text_input("Notes (optional)", key=f"notes_{idx}")

vote_cols = st.columns(4)
with vote_cols[0]:
    if st.button("A is better", key=f"vote_a_{idx}", use_container_width=True):
        # Map back to actual result IDs
        winner = left_id if not swapped else ("a" if left_id == "b" else "b")
        asyncio.get_event_loop().run_until_complete(
            store.insert_comparison(posting_id, a_by_posting[posting_id]["id"],
                                     b_by_posting[posting_id]["id"], "a", notes)
        )
        st.session_state.review_idx = min(idx + 1, len(common_ids) - 1)
        st.rerun()
with vote_cols[1]:
    if st.button("B is better", key=f"vote_b_{idx}", use_container_width=True):
        asyncio.get_event_loop().run_until_complete(
            store.insert_comparison(posting_id, a_by_posting[posting_id]["id"],
                                     b_by_posting[posting_id]["id"], "b", notes)
        )
        st.session_state.review_idx = min(idx + 1, len(common_ids) - 1)
        st.rerun()
with vote_cols[2]:
    if st.button("Tie", key=f"vote_tie_{idx}", use_container_width=True):
        asyncio.get_event_loop().run_until_complete(
            store.insert_comparison(posting_id, a_by_posting[posting_id]["id"],
                                     b_by_posting[posting_id]["id"], "tie", notes)
        )
        st.session_state.review_idx = min(idx + 1, len(common_ids) - 1)
        st.rerun()
with vote_cols[3]:
    if st.button("Both bad", key=f"vote_bad_{idx}", use_container_width=True):
        asyncio.get_event_loop().run_until_complete(
            store.insert_comparison(posting_id, a_by_posting[posting_id]["id"],
                                     b_by_posting[posting_id]["id"], "both_bad", notes)
        )
        st.session_state.review_idx = min(idx + 1, len(common_ids) - 1)
        st.rerun()

# --- Navigation ---
nav_cols = st.columns(2)
with nav_cols[0]:
    if st.button("← Previous") and idx > 0:
        st.session_state.review_idx = idx - 1
        st.rerun()
with nav_cols[1]:
    if st.button("Next →") and idx < len(common_ids) - 1:
        st.session_state.review_idx = idx + 1
        st.rerun()
```

**Step 3: Verify it loads**

```bash
cd compgraph-eval && uv run streamlit run eval/ui/app.py
```
Expected: Review page renders (will show "Need at least 2 runs" until data exists)

**Step 4: Commit**

```bash
git add eval/ui/components.py eval/ui/pages/2_Review.py
git commit -m "feat: add side-by-side review page with diff highlighting"
```

---

## Task 11: Streamlit UI — Page 3 (Leaderboard)

**Files:**
- Create: `compgraph-eval/eval/ui/pages/3_Leaderboard.py`

**Step 1: Write Page 3**

```python
# compgraph-eval/eval/ui/pages/3_Leaderboard.py
"""Page 3: Elo leaderboard and field-level accuracy."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from eval.elo import calculate_elo_ratings
from eval.store import EvalStore

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
DB_PATH = str(DATA_DIR / "eval.db")


@st.cache_resource
def get_store() -> EvalStore:
    store = EvalStore(DB_PATH)
    asyncio.get_event_loop().run_until_complete(store.init())
    return store


store = get_store()
st.header("Leaderboard")

# --- Load data ---
runs = asyncio.get_event_loop().run_until_complete(store.get_all_runs())
comparisons = asyncio.get_event_loop().run_until_complete(store.get_comparisons())

if not runs:
    st.info("No runs yet.")
    st.stop()

# --- Filter by pass ---
pass_number = st.selectbox("Pass", [1, 2])
pass_runs = [r for r in runs if r["pass_number"] == pass_number]

if not pass_runs:
    st.info(f"No Pass {pass_number} runs yet.")
    st.stop()

# --- Build run_map: result_id → "model/prompt" label ---
run_map: dict[int, str] = {}
run_labels: dict[int, str] = {}  # run_id → label
for run in pass_runs:
    label = f"{run['model']}/{run['prompt_version']}"
    run_labels[run["id"]] = label
    results = asyncio.get_event_loop().run_until_complete(store.get_results(run["id"]))
    for r in results:
        run_map[r["id"]] = label

# --- Elo ratings ---
if comparisons:
    ratings = calculate_elo_ratings(comparisons, run_map)
else:
    ratings = {label: 1500 for label in set(run_map.values())}

# --- Build leaderboard table ---
leaderboard = []
for run in pass_runs:
    label = run_labels[run["id"]]
    results = asyncio.get_event_loop().run_until_complete(store.get_results(run["id"]))
    total = len(results)
    success = sum(1 for r in results if r["parse_success"])

    # Count wins for this combo
    wins = sum(
        1 for c in comparisons
        if (run_map.get(c["result_a_id"]) == label and c["winner"] == "a")
        or (run_map.get(c["result_b_id"]) == label and c["winner"] == "b")
    )
    total_comps = sum(
        1 for c in comparisons
        if run_map.get(c["result_a_id"]) == label
        or run_map.get(c["result_b_id"]) == label
    )

    leaderboard.append({
        "Model/Prompt": label,
        "Elo": round(ratings.get(label, 1500)),
        "Win %": f"{wins/total_comps*100:.0f}%" if total_comps > 0 else "—",
        "Parse Rate": f"{success}/{total}",
        "Cost": f"${run.get('total_cost_usd', 0) or 0:.4f}",
        "Latency": f"{(run.get('total_duration_ms', 0) or 0)/1000:.1f}s",
    })

leaderboard.sort(key=lambda x: x["Elo"], reverse=True)
st.dataframe(pd.DataFrame(leaderboard), use_container_width=True, hide_index=True)

# --- Field-level accuracy (Pass 1 only) ---
if pass_number == 1 and pass_runs:
    st.subheader("Field-Level Population Rate")
    st.caption("Percentage of postings where each field was non-null, by run.")

    fields = [
        "role_archetype", "role_level", "employment_type",
        "pay_type", "pay_min", "pay_max",
        "has_commission", "has_benefits",
        "tools_mentioned", "kpis_mentioned", "store_count",
    ]

    field_data = []
    for run in pass_runs:
        label = run_labels[run["id"]]
        results = asyncio.get_event_loop().run_until_complete(store.get_results(run["id"]))
        parsed = [json.loads(r["parsed_result"]) for r in results if r["parsed_result"]]
        total = len(parsed) if parsed else 1

        row = {"Model/Prompt": label}
        for f in fields:
            non_null = sum(
                1 for p in parsed
                if p.get(f) is not None and p.get(f) != [] and p.get(f) != ""
            )
            row[f] = f"{non_null/total*100:.0f}%"
        field_data.append(row)

    if field_data:
        st.dataframe(pd.DataFrame(field_data), use_container_width=True, hide_index=True)
```

**Step 2: Verify it loads**

```bash
cd compgraph-eval && uv run streamlit run eval/ui/app.py
```
Expected: Leaderboard page renders (will show "No runs yet" until data exists)

**Step 3: Commit**

```bash
git add eval/ui/pages/3_Leaderboard.py
git commit -m "feat: add Elo leaderboard page with field-level accuracy"
```

---

## Task 12: End-to-End Smoke Test

**Files:**
- Create: `compgraph-eval/tests/test_e2e.py`

A full integration test that runs the entire flow with mocked LLM calls.

**Step 1: Write the test**

```python
# compgraph-eval/tests/test_e2e.py
"""End-to-end smoke test: corpus → run → compare → elo."""

import json
import pytest
import pytest_asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

from eval.store import EvalStore
from eval.runner import run_evaluation
from eval.elo import calculate_elo_ratings
from eval.providers import LLMResponse


@pytest_asyncio.fixture
async def store(tmp_path: Path):
    s = EvalStore(str(tmp_path / "test.db"))
    await s.init()
    yield s
    await s.close()


@pytest.fixture
def corpus_file(tmp_path: Path) -> Path:
    postings = [
        {"id": "p1", "company_slug": "bds", "title": "Field Rep",
         "location": "Atlanta", "full_text": "Visit stores. $18/hr."},
        {"id": "p2", "company_slug": "troc", "title": "Merchandiser",
         "location": "Dallas", "full_text": "Stock shelves at Target."},
    ]
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(postings))
    return path


@pytest.mark.asyncio
async def test_full_flow(store: EvalStore, corpus_file: Path):
    """Run two evaluations, add comparisons, compute Elo."""
    good_response = LLMResponse(
        content='{"role_archetype": "field_rep", "pay_min": 18.0, "pay_max": 18.0}',
        input_tokens=500, output_tokens=100, cost_usd=0.002, latency_ms=800,
    )
    weak_response = LLMResponse(
        content='{"role_archetype": "field_rep"}',
        input_tokens=400, output_tokens=80, cost_usd=0.001, latency_ms=600,
    )

    # Run A: "good" model
    with patch("eval.runner.call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = good_response
        summary_a = await run_evaluation(store, 1, "haiku-4.5", "pass1_v1", str(corpus_file))
    assert summary_a.succeeded == 2

    # Run B: "weak" model — delete unique constraint conflict first
    # The UNIQUE on (pass_number, model, prompt_version) means we need different model
    with patch("eval.runner.call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = weak_response
        summary_b = await run_evaluation(store, 1, "gpt-4o-mini", "pass1_v1", str(corpus_file))
    assert summary_b.succeeded == 2

    # Get results for comparisons
    results_a = await store.get_results(summary_a.run_id)
    results_b = await store.get_results(summary_b.run_id)

    # Add comparisons: A wins both
    for ra, rb in zip(results_a, results_b):
        await store.insert_comparison(ra["posting_id"], ra["id"], rb["id"], "a")

    # Compute Elo
    comparisons = await store.get_comparisons()
    run_map = {}
    for r in results_a:
        run_map[r["id"]] = "haiku-4.5/pass1_v1"
    for r in results_b:
        run_map[r["id"]] = "gpt-4o-mini/pass1_v1"

    ratings = calculate_elo_ratings(comparisons, run_map)
    assert ratings["haiku-4.5/pass1_v1"] > ratings["gpt-4o-mini/pass1_v1"]
    assert ratings["haiku-4.5/pass1_v1"] > 1500
```

**Step 2: Run all tests**

```bash
cd compgraph-eval && uv run pytest -v
```
Expected: All tests PASS (schemas: 8, store: 6, prompts: 7, providers: 3, runner: 3, elo: 4, e2e: 1 = ~32 tests)

**Step 3: Commit**

```bash
git add tests/test_e2e.py
git commit -m "test: add end-to-end smoke test for full eval flow"
```

---

## Summary

| Task | Description | Files | Tests |
|------|-------------|-------|-------|
| 1 | Project scaffolding | pyproject.toml, .gitignore, dirs | — |
| 2 | Schemas & config | schemas.py, config.py | 8 |
| 3 | SQLite store | store.py | 6 |
| 4 | Prompt registry | prompts/__init__.py, pass1_v1.py, pass2_v1.py | 7 |
| 5 | LLM provider wrapper | providers.py | 3 |
| 6 | Runner engine | runner.py | 3 |
| 7 | Elo calculator | elo.py | 4 |
| 8 | Corpus export script | scripts/export_corpus.py | — |
| 9 | UI: Run Tests page | ui/app.py, ui/pages/1_Run_Tests.py | — |
| 10 | UI: Review page | ui/pages/2_Review.py, ui/components.py | — |
| 11 | UI: Leaderboard page | ui/pages/3_Leaderboard.py | — |
| 12 | E2E smoke test | tests/test_e2e.py | 1 |

**Total: 12 tasks, ~15 files, ~32 tests, 12 commits**

Plan complete and saved to `docs/plans/2026-02-19-llm-eval-tool-plan.md`.

---

**Two execution options:**

**1. Subagent-Driven (this session)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** — Open a new session with executing-plans, batch execution with checkpoints

Which approach?