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
    total_duration_ms INTEGER
);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
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
    result_a_id INTEGER NOT NULL REFERENCES results(id) ON DELETE CASCADE,
    result_b_id INTEGER NOT NULL REFERENCES results(id) ON DELETE CASCADE,
    winner TEXT NOT NULL CHECK (winner IN ('a', 'b', 'tie', 'both_bad')),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS field_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT DEFAULT (datetime('now')),
    result_id INTEGER NOT NULL REFERENCES results(id) ON DELETE CASCADE,
    field_name TEXT NOT NULL,
    model_value TEXT,
    is_correct INTEGER NOT NULL,
    correct_value TEXT,
    UNIQUE(result_id, field_name)
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
        await self._db.execute("PRAGMA foreign_keys = ON")
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
            (
                total_input_tokens,
                total_output_tokens,
                total_cost_usd,
                total_duration_ms,
                run_id,
            ),
        )
        await self._db.commit()

    async def delete_run(self, run_id: int) -> None:
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
                run_id,
                posting_id,
                raw_response,
                json.dumps(parsed_result) if parsed_result else None,
                parse_success,
                input_tokens,
                output_tokens,
                cost_usd,
                latency_ms,
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
        cursor = await self._db.execute(
            "SELECT * FROM results WHERE id = ?", (result_id,)
        )
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
            "SELECT * FROM comparisons ORDER BY created_at ASC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # --- Run Lookup ---

    async def find_run(
        self, pass_number: int, model: str, prompt_version: str
    ) -> dict | None:
        """Find an existing run by pass/model/prompt combo. Returns dict or None."""
        cursor = await self._db.execute(
            """SELECT * FROM runs
               WHERE pass_number = ? AND model = ? AND prompt_version = ?
               ORDER BY created_at DESC LIMIT 1""",
            (pass_number, model, prompt_version),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    # --- Field Reviews ---

    async def upsert_field_review(
        self,
        result_id: int,
        field_name: str,
        model_value: str | None,
        is_correct: int,
        correct_value: str | None = None,
    ) -> int:
        """Insert or update a field review. Returns the review id."""
        cursor = await self._db.execute(
            """INSERT INTO field_reviews (result_id, field_name, model_value, is_correct, correct_value)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(result_id, field_name) DO UPDATE SET
                   model_value = excluded.model_value,
                   is_correct = excluded.is_correct,
                   correct_value = excluded.correct_value,
                   created_at = datetime('now')""",
            (result_id, field_name, model_value, is_correct, correct_value),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def get_all_field_reviews_for_run(self, run_id: int) -> dict[int, list[dict]]:
        """Bulk-load all field reviews for a run, keyed by result_id.

        Avoids N+1 queries during ground truth extraction.
        """
        cursor = await self._db.execute(
            """SELECT fr.* FROM field_reviews fr
               JOIN results r ON fr.result_id = r.id
               WHERE r.run_id = ? ORDER BY fr.result_id, fr.field_name""",
            (run_id,),
        )
        rows = await cursor.fetchall()
        grouped: dict[int, list[dict]] = {}
        for row in rows:
            d = dict(row)
            grouped.setdefault(d["result_id"], []).append(d)
        return grouped

    async def get_runs_with_reviews(self) -> list[dict]:
        """Get runs that have at least one field review — for baseline selectors."""
        cursor = await self._db.execute(
            """SELECT DISTINCT r.* FROM runs r
               JOIN results res ON res.run_id = r.id
               JOIN field_reviews fr ON fr.result_id = res.id
               ORDER BY r.created_at DESC"""
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_field_reviews(self, result_id: int) -> list[dict]:
        """Get all field reviews for a specific result."""
        cursor = await self._db.execute(
            "SELECT * FROM field_reviews WHERE result_id = ? ORDER BY field_name",
            (result_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_result_run_map(self) -> dict[int, str]:
        cursor = await self._db.execute(
            "SELECT r.id, ru.model, ru.prompt_version FROM results r JOIN runs ru ON r.run_id = ru.id"
        )
        rows = await cursor.fetchall()
        return {row["id"]: f"{row['model']}/{row['prompt_version']}" for row in rows}

    async def get_field_accuracy(self, run_id: int) -> dict[str, float]:
        """Get per-field accuracy from human reviews for a run.

        Excludes is_correct = -1 (can't assess) from accuracy calculations.
        """
        cursor = await self._db.execute(
            """SELECT fr.field_name,
                      AVG(fr.is_correct) as accuracy,
                      COUNT(*) as reviewed
               FROM field_reviews fr
               JOIN results r ON fr.result_id = r.id
               WHERE r.run_id = ? AND fr.is_correct >= 0
               GROUP BY fr.field_name""",
            (run_id,),
        )
        rows = await cursor.fetchall()
        return {row["field_name"]: row["accuracy"] for row in rows}

    async def delete_field_review(self, result_id: int, field_name: str) -> None:
        await self._db.execute(
            "DELETE FROM field_reviews WHERE result_id = ? AND field_name = ?",
            (result_id, field_name),
        )
        await self._db.commit()

    async def get_reviewed_count(self, run_id: int) -> int:
        """Count how many results in a run have at least one field review."""
        cursor = await self._db.execute(
            """SELECT COUNT(DISTINCT fr.result_id)
               FROM field_reviews fr
               JOIN results r ON fr.result_id = r.id
               WHERE r.run_id = ?""",
            (run_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0
