# Design: CompGraph LLM Evaluation Tool

**Date:** 2026-02-19
**Status:** Approved

## Purpose

Standalone tool for testing and comparing LLM model/prompt combinations against CompGraph's enrichment pipeline. Enables data-driven decisions about which model and prompt version to use for Pass 1 (classification) and Pass 2 (entity extraction) by running side-by-side human reviews with Elo ranking.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  compgraph-eval                      │
│                                                      │
│  ┌──────────┐    ┌──────────┐    ┌───────────────┐  │
│  │  Corpus   │───▶│  Runner   │───▶│  SQLite Store │  │
│  │ (Supabase │    │          │    │               │  │
│  │  export)  │    │ LiteLLM  │    │ runs, results │  │
│  └──────────┘    │ + prompt  │    │ comparisons   │  │
│                  │ registry  │    │ elo_scores    │  │
│                  └──────────┘    └───────┬───────┘  │
│                                          │          │
│                              ┌───────────▼───────┐  │
│                              │   Streamlit UI    │  │
│                              │                   │  │
│                              │ • Run tests       │  │
│                              │ • Side-by-side    │  │
│                              │ • Leaderboard     │  │
│                              └───────────────────┘  │
└─────────────────────────────────────────────────────┘
```

- **Corpus**: One-time export of 50-100 real postings from Supabase → local JSON file
- **Runner**: Executes (prompt version × model) matrix via LiteLLM, stores results in SQLite
- **Streamlit UI**: Run tests, side-by-side human review, Elo leaderboard
- **CompGraph schema**: Pass1Result/Pass2Result Pydantic models copied (~60 lines) rather than full package dependency

## Data Model (SQLite)

```sql
CREATE TABLE corpus (
    id TEXT PRIMARY KEY,
    company_slug TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT,
    full_text TEXT NOT NULL,
    reference_pass1 JSON,
    reference_pass2 JSON
);

CREATE TABLE runs (
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

CREATE TABLE results (
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

CREATE TABLE comparisons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    posting_id TEXT NOT NULL REFERENCES corpus(id),
    result_a_id INTEGER NOT NULL REFERENCES results(id),
    result_b_id INTEGER NOT NULL REFERENCES results(id),
    winner TEXT NOT NULL CHECK (winner IN ('a', 'b', 'tie', 'both_bad')),
    notes TEXT
);
```

Elo scores computed on the fly from comparisons table — not stored.

## Project Structure

```
compgraph-eval/
├── pyproject.toml
├── .env                       # API keys (git-ignored)
├── eval/
│   ├── __init__.py
│   ├── config.py              # MODELS dict (alias → LiteLLM model string)
│   ├── schemas.py             # Pass1Result, Pass2Result, EntityMention (copied from CompGraph)
│   ├── runner.py              # Test execution engine
│   ├── providers.py           # LiteLLM wrapper + cost tracking
│   ├── store.py               # SQLite via aiosqlite (schema init, CRUD)
│   ├── corpus.py              # Export postings from Supabase → corpus.json
│   ├── elo.py                 # Elo rating calculator
│   ├── prompts/
│   │   ├── __init__.py        # Auto-discovers prompt modules
│   │   ├── pass1_v1.py        # Production baseline prompt
│   │   ├── pass2_v1.py        # Production baseline prompt
│   │   └── ...                # User-created variants
│   └── ui/
│       ├── app.py             # Streamlit entry point
│       ├── pages/
│       │   ├── 1_Run_Tests.py
│       │   ├── 2_Review.py
│       │   └── 3_Leaderboard.py
│       └── components.py      # Shared UI helpers (diff highlighting)
├── data/
│   ├── corpus.json            # Exported test postings (git-ignored)
│   └── eval.db                # SQLite database (git-ignored)
└── scripts/
    └── export_corpus.py       # One-time: pull postings from Supabase
```

## Model Configuration

```python
# eval/config.py
MODELS = {
    "haiku-4.5": "claude-haiku-4-5-20251001",
    "sonnet-4.5": "claude-sonnet-4-5-20241022",
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-4o": "gpt-4o",
    "gemini-flash": "gemini/gemini-2.0-flash",
    "deepseek-v3": "deepseek/deepseek-chat",
}
# API keys from .env, auto-detected by LiteLLM
```

Add a model = add one line. LiteLLM handles auth, message format, token counting.

## Prompt Registry

Each prompt version is a Python file exporting `SYSTEM_PROMPT` (str) and `build_user_message()` (function). Auto-discovered by scanning `eval/prompts/` for `pass{N}_*.py` files.

**Workflow**: copy baseline → edit in editor → run evaluation → review side-by-side → promote winner to CompGraph production.

## Runner

- Loads corpus from JSON, loads prompt module dynamically
- Executes via `litellm.acompletion()` with configurable concurrency (default 5)
- Captures: raw response, parsed result, parse success, tokens, cost, latency
- Pass 2 uses `content_role_specific` from best Pass 1 run or production enrichment
- Parse failures stored (not skipped) — failure rate is signal

## Streamlit UI

**Page 1 — Run Tests**: Form (pass, model, prompt dropdowns) + run history table (success rate, cost, latency).

**Page 2 — Review**: Side-by-side comparison for one posting at a time. Diff highlighting on disagreeing fields. Randomized A/B assignment to avoid position bias. Keyboard shortcuts (1=A, 2=B, 3=Tie, 4=Both bad). Notes field. Navigation (prev/next, progress counter).

**Page 3 — Leaderboard**: Elo rankings per pass. Win rate and cost columns. Per-field accuracy breakdown (population rate, null % by field across runs).

## Dependencies

```toml
[project]
dependencies = [
    "litellm",
    "streamlit",
    "aiosqlite",
    "pydantic>=2.0",
]

[project.optional-dependencies]
export = ["asyncpg", "sqlalchemy[asyncio]"]
```

## What's NOT in scope

- No prompt editing UI — edit Python files in your editor
- No automated golden dataset scoring — human review only (for now)
- No CI/CD — local tool
- No entity resolution testing — only LLM output quality (Pass 1 and Pass 2 results)
- No production deployment — runs on your laptop
