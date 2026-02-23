# Design: Wire Python Eval Backend to Next.js Frontend via FastAPI

**Date:** 2026-02-21
**Status:** Approved
**Issue:** #14

## Purpose

Add a FastAPI API layer that exposes the existing Python eval backend over HTTP, then wire all Next.js frontend pages to consume real data instead of hardcoded mock arrays. This makes the eval tool fully interactive: run tests, vote on comparisons, mark field judgments, and view live leaderboard data.

## Architecture

```
compgraph-eval/
├── eval/
│   ├── api.py          ← NEW: FastAPI app (HTTP glue only)
│   ├── store.py        existing SQLite CRUD (78 tests)
│   ├── runner.py       existing LLM execution
│   ├── elo.py          existing Elo calculator
│   ├── providers.py    existing LiteLLM wrapper
│   ├── prompts/        existing prompt registry
│   ├── validator.py    existing
│   └── ground_truth.py existing
│
├── web/
│   ├── src/lib/api-client.ts  ← NEW: typed fetch wrapper
│   ├── src/app/               pages (rewired to API)
│   └── next.config.ts         proxy /api/* → :8001
│
└── data/eval.db               shared SQLite file
```

**Communication:** Next.js (port 3000) → proxy rewrite → FastAPI (port 8001). No CORS needed — same-origin in dev via Next.js rewrites, reverse proxy in prod via Caddy.

## API Endpoints

| Method | Endpoint | Backend | Frontend Consumer |
|--------|----------|---------|-------------------|
| GET | /api/runs | store.get_all_runs() | Dashboard, Runs |
| POST | /api/runs | runner.run_evaluation() | Run Tests form |
| GET | /api/runs/{id} | store.get_run(id) | Run detail |
| DELETE | /api/runs/{id} | store.delete_run(id) | Run management |
| GET | /api/runs/{id}/results | store.get_results(id) | Review, Accuracy |
| GET | /api/runs/{id}/progress | in-memory dict lookup | Run Tests progress |
| GET | /api/runs/{id}/field-accuracy | store.get_field_accuracy(id) | Leaderboard |
| GET | /api/runs/{id}/field-reviews | store.get_all_field_reviews_for_run(id) | Accuracy Review |
| GET | /api/corpus | store.get_corpus() | Review, Accuracy |
| GET | /api/comparisons | store.get_comparisons() | Leaderboard |
| POST | /api/comparisons | store.insert_comparison() | Review voting |
| GET | /api/elo | elo.calculate_elo_ratings() | Leaderboard |
| GET | /api/config/models | config.MODELS | Run form dropdowns |
| GET | /api/config/prompts/{pass_number} | prompts.list_prompts() | Run form dropdowns |
| POST | /api/field-reviews | store.upsert_field_review() | Accuracy Review |

### Run Execution (POST /api/runs)

Long-running operation (minutes for 50 postings). Design:
1. POST /api/runs returns immediately with `{ "run_id": N, "status": "running" }`
2. Runner executes in a background asyncio task
3. Progress stored in an in-memory dict: `{ completed: 12, total: 50, status: "running" }`
4. Frontend polls GET /api/runs/{id}/progress every 2 seconds
5. When complete, progress dict shows `{ status: "completed", summary: {...} }`

## Frontend Changes

### New: src/lib/api-client.ts

Single module for all backend communication. Typed return values matching existing TypeScript interfaces from mock-data.ts. Functions:

- getRuns() → EvalRun[]
- createRun(params) → { runId: number }
- getRunProgress(id) → { completed, total, status }
- getCorpus() → CorpusPosting[]
- getRunResults(id) → Result[]
- postComparison(params) → { id: number }
- getEloRatings() → Record<string, number>
- getModels() → Record<string, string>
- getPrompts(pass) → string[]
- postFieldReview(params) → { id: number }
- getFieldReviews(runId) → Record<number, FieldReview[]>
- getFieldAccuracy(runId) → Record<string, number>

### Page Rewiring

**Run Tests** (`/runs`):
- Add form: pass selector, model dropdown, prompt dropdown (populated from /api/config/*)
- "New Run" button → POST /api/runs → show progress bar polling /api/runs/{id}/progress
- Table populated from GET /api/runs

**Review** (`/review`):
- Run selector dropdowns (populated from GET /api/runs)
- Load results for both runs, find common posting IDs
- Randomized A/B assignment (client-side, per-session)
- Vote buttons → POST /api/comparisons → advance to next posting
- Navigation: prev/next with progress counter
- Notes text field included in comparison POST

**Accuracy Review** (`/accuracy`):
- Run selector dropdown
- Load corpus + results for selected run
- Navigate through postings with prev/next
- Per-field judgment buttons (correct/wrong/can't assess) → POST /api/field-reviews
- Show ground truth when available (from reference_pass1 in corpus)

**Leaderboard** (`/leaderboard`):
- Elo table from GET /api/elo (computed from comparisons)
- Field population rate from GET /api/runs/{id}/field-accuracy per run
- Pass filter (Pass 1 / Pass 2) as client-side filter

**Prompt Diff** (`/prompt-diff`):
- Run selector dropdowns (baseline + candidate)
- Load results for both runs, compute diff client-side
- Summary metrics computed from field-level comparison

**Dashboard** (`/`):
- KPI cards computed from GET /api/runs
- Recent runs table from GET /api/runs
- Review progress from field review counts

## Dev Workflow

Two terminals:
```bash
# Terminal 1: Python API
cd compgraph-eval && uv run uvicorn eval.api:app --port 8001 --reload

# Terminal 2: Next.js
cd compgraph-eval/web && npm run dev
```

Next.js proxy in next.config.ts rewrites /api/* to localhost:8001/api/*.

## Deployment (Pi)

Two systemd services. Caddy reverse proxy routes /api/* to port 8001, everything else to port 3000.

## Testing

- **Python**: tests/test_api.py — httpx.AsyncClient against FastAPI TestClient. Covers HTTP status codes, request/response shapes, error cases. Business logic already tested (78 tests).
- **Next.js**: Update Vitest tests to mock api-client.ts functions. Existing component tests still valid (they test rendering, not data source).
- **No E2E tests** this phase.

## Not In Scope

- Auth (local/LAN tool only)
- WebSocket/SSE streaming (poll-based progress sufficient)
- SQLite schema changes (existing 5 tables cover all needs)
- Removing mock-data.ts (keep as fallback/storybook data)
- Replacing Streamlit UI (already superseded by Next.js)
