# Vercel-to-DO Timeout Patterns

> Reference for CompGraph long-running operations. Covers Vercel proxy timeouts,
> HTTP 202 + polling pattern, FastAPI background tasks, and SWR polling configuration.
> Context: Frontend on Vercel (rewrites `/api/*` → `dev.compgraph.io`), backend on
> DO Droplet (FastAPI), enrichment jobs take 2-5 min, aggregation rebuilds take 30-60s.

---

## Quick Reference

| Timeout | Limit | Applies to |
|---------|-------|------------|
| Vercel proxy rewrite (CDN origin) | **120s** to first byte | `/api/*` → `dev.compgraph.io` rewrites |
| Vercel proxy rewrite (streaming) | 120s between chunks | After first byte received |
| Vercel Serverless Function (Hobby) | 10s (standard) / 60s (Fluid) | Next.js API routes, SSR |
| Vercel Serverless Function (Pro) | 60s (standard) / 800s (Fluid) | Next.js API routes, SSR |
| Vercel Middleware | 30s | Edge middleware |

**CompGraph-critical limit:** The 120s CDN origin timeout on the `/api/*` rewrite. If the FastAPI backend takes >120s to send the first byte, Vercel returns `ROUTER_EXTERNAL_TARGET_ERROR` (504).

---

## S1 The Timeout Problem

### What happens today

```
Browser → Vercel Edge (rewrite) → dev.compgraph.io (FastAPI)
                                   └── enrichment: 2-5 min ❌
                                   └── aggregation: 30-60s ⚠️
                                   └── normal API: <1s ✓
```

| Operation | Duration | Vercel proxy result |
|-----------|----------|-------------------|
| Normal API query | <1s | 200 OK |
| Aggregation rebuild | 30-60s | 200 OK (under 120s limit) |
| Enrichment backfill | 2-5 min | **504 ROUTER_EXTERNAL_TARGET_ERROR** |
| Full pipeline (scrape→enrich→agg) | 5-15 min | **504** |

### Why Vercel's timeout exists

The 120s limit is at the CDN/proxy layer — it is not configurable per-project. After the first byte arrives, the proxy allows another 120s per chunk (supports streaming). But enrichment/pipeline endpoints block until completion, sending no bytes until done.

---

## S2 HTTP 202 + Polling Pattern

The standard solution: return immediately with a job ID, poll a status endpoint.

### FastAPI Backend

```python
# src/compgraph/api/routes/pipeline.py
import uuid
from datetime import datetime, timezone
from enum import Enum

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    success = "success"
    partial = "partial"
    failed = "failed"


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    started_at: datetime
    completed_at: datetime | None = None
    detail: str | None = None
    progress: int | None = None  # 0-100


# In-memory store (replace with Redis/DB for multi-process)
_jobs: dict[str, JobResponse] = {}


@router.post("/enrichment/trigger", status_code=202)
async def trigger_enrichment(background_tasks: BackgroundTasks) -> JobResponse:
    """Start enrichment. Returns 202 immediately with job_id for polling."""
    job_id = str(uuid.uuid4())
    job = JobResponse(
        job_id=job_id,
        status=JobStatus.pending,
        started_at=datetime.now(timezone.utc),
    )
    _jobs[job_id] = job
    background_tasks.add_task(_run_enrichment, job_id)
    return job


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> JobResponse:
    """Poll job status. Frontend calls this every N seconds."""
    if job_id not in _jobs:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")
    return _jobs[job_id]


async def _run_enrichment(job_id: str) -> None:
    """Background task. Updates job status as it progresses."""
    job = _jobs[job_id]
    job.status = JobStatus.running
    try:
        # ... actual enrichment work with progress updates ...
        job.progress = 50
        # ... more work ...
        job.status = JobStatus.success
        job.progress = 100
    except Exception as e:
        job.status = JobStatus.failed
        job.detail = str(e)
    finally:
        job.completed_at = datetime.now(timezone.utc)
```

### Key design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Job store | In-memory dict | CompGraph runs single-process on one Droplet. Switch to Redis when arq replaces APScheduler (M8). |
| Background executor | `BackgroundTasks` | Runs in the same event loop. Sufficient for single-worker. Use Celery/arq for multi-worker. |
| Progress tracking | Integer 0-100 | Simple. Frontend shows progress bar. |
| Terminal states | `success`, `partial`, `failed` | Matches existing pipeline status conventions. |

---

## S3 Frontend Polling with SWR

### Basic polling hook

```typescript
// src/lib/hooks/useJobStatus.ts
import useSWR from "swr";
import { api } from "@/lib/api-client";

const TERMINAL = new Set(["success", "partial", "failed"]);

interface JobStatus {
  job_id: string;
  status: "pending" | "running" | "success" | "partial" | "failed";
  started_at: string;
  completed_at: string | null;
  detail: string | null;
  progress: number | null;
}

export function useJobStatus(jobId: string | null) {
  const { data, error, isLoading } = useSWR<JobStatus>(
    jobId ? `/api/v1/pipeline/jobs/${jobId}` : null,
    (url: string) => apiFetch<JobStatus>(url),
    {
      refreshInterval: (data) => {
        if (!data) return 3000; // Poll every 3s while loading
        if (TERMINAL.has(data.status)) return 0; // Stop polling
        return 3000;
      },
      revalidateOnFocus: true, // Recheck when tab regains focus
      refreshWhenHidden: false, // Don't waste requests when tab hidden
      refreshWhenOffline: false, // Don't poll when offline
      dedupingInterval: 2000, // Dedup rapid re-renders
    }
  );

  return {
    job: data ?? null,
    error: error?.message ?? null,
    isLoading,
    isTerminal: data ? TERMINAL.has(data.status) : false,
  };
}
```

### SWR polling behavior

| Scenario | Behavior |
|----------|----------|
| Tab active, job running | Polls every 3s |
| Tab hidden, job running | **Stops polling** (`refreshWhenHidden: false`) |
| Tab refocused | Immediately revalidates (`revalidateOnFocus: true`) |
| Job reaches terminal state | **Stops polling** (`refreshInterval` returns 0) |
| Network offline | **Stops polling** (`refreshWhenOffline: false`) |

### UI state transitions

```typescript
// src/components/pipeline/TriggerButton.tsx
function TriggerButton() {
  const [jobId, setJobId] = useState<string | null>(null);
  const { job, isTerminal } = useJobStatus(jobId);

  const handleTrigger = async () => {
    const res = await api.triggerEnrichment(); // POST, returns 202
    setJobId(res.job_id);
  };

  if (!jobId) return <Button onClick={handleTrigger}>Run Enrichment</Button>;
  if (!job) return <Button disabled>Starting...</Button>;

  return (
    <div>
      <Button disabled={!isTerminal} onClick={() => setJobId(null)}>
        {isTerminal ? "Run Again" : "Processing..."}
      </Button>
      {job.progress != null && <ProgressBar value={job.progress} />}
      {job.status === "failed" && <Alert>{job.detail}</Alert>}
    </div>
  );
}
```

---

## S4 Error Handling: Vercel Timeout vs Backend Continuation

When Vercel times out but the backend keeps running, there is a split-brain scenario.

### The problem

```
1. Frontend → POST /api/v1/pipeline/enrichment/trigger → 202 {job_id: "abc"}
2. Frontend polls GET /api/v1/pipeline/jobs/abc → 200 {status: "running"}
3. Vercel proxy times out on a poll request (120s limit hit due to network stall)
4. Frontend gets 504 — but backend job is still running
```

### Mitigation

```typescript
// Retry on 504, don't treat as job failure
const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (res.status === 504) {
    // Vercel proxy timeout — backend is likely still processing
    // Return stale data, SWR will retry on next interval
    throw new Error("Gateway timeout — retrying");
  }
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
};

// SWR handles retry automatically via errorRetryCount / errorRetryInterval
useSWR(key, fetcher, {
  errorRetryCount: 5,
  errorRetryInterval: 5000, // Retry after 5s on error
});
```

### What about streaming?

Vercel's 120s timeout resets on each chunk. If the backend streams progress, the timeout is avoided:

```python
# FastAPI streaming response (alternative to polling)
from fastapi.responses import StreamingResponse
import asyncio, json

async def enrichment_stream():
    yield json.dumps({"status": "running", "progress": 0}) + "\n"
    for i in range(100):
        await asyncio.sleep(1)  # Simulate work
        yield json.dumps({"status": "running", "progress": i + 1}) + "\n"
    yield json.dumps({"status": "success", "progress": 100}) + "\n"

@router.post("/enrichment/stream")
async def trigger_enrichment_stream():
    return StreamingResponse(enrichment_stream(), media_type="application/x-ndjson")
```

**Trade-off:** Streaming is simpler but requires the connection to stay open for the full duration. Polling is more resilient to network interruptions and tab switches. **Recommendation: Use polling for CompGraph** — enrichment jobs are 2-5 min, users will switch tabs.

---

## S5 FastAPI BackgroundTasks vs Job Queue

| Feature | `BackgroundTasks` | arq (M8 roadmap) | Celery |
|---------|-------------------|-------------------|--------|
| Setup complexity | Zero | Needs Redis | Needs Redis + worker |
| Multi-worker | No | Yes | Yes |
| Retries | Manual | Built-in | Built-in |
| Progress tracking | Manual (in-memory) | Built-in | Built-in |
| Job persistence | None (lost on restart) | Redis-backed | Redis/DB-backed |
| Suitable for CompGraph now? | **Yes** (single Droplet) | M8 target | Overkill |

**Current recommendation:** Use `BackgroundTasks` + in-memory job dict. The single-Droplet deployment means no worker coordination is needed. When arq is adopted in M8, migrate the job dict to Redis and the background tasks to arq workers.

**Caveat:** If the Droplet restarts mid-enrichment, in-flight jobs are lost. Acceptable for dev/staging. For production, persist job state to the `pipeline_runs` table already used by APScheduler.

---

## Gotchas & Limitations

| Issue | Impact | Mitigation |
|-------|--------|------------|
| Vercel proxy 120s to first byte | Enrichment (2-5 min) returns 504 | Use 202 + polling pattern (S2) |
| `BackgroundTasks` runs in event loop | CPU-heavy work blocks API | Use `asyncio.to_thread()` for CPU-bound enrichment steps |
| In-memory job dict lost on restart | Running jobs disappear | Persist to DB; check on startup |
| SWR polls with stale `jobId` after HMR | Dev-only: phantom polls | Clear jobId state on component unmount |
| Vercel Hobby plan: 10s function timeout | SSR pages calling slow endpoints timeout | Use client-side fetching (`"use client"` + `useEffect`), not `getServerSideProps` |
| `refreshWhenHidden: false` + long tab switch | User returns to stale status | `revalidateOnFocus: true` handles this |
| Multiple users triggering same pipeline | Race condition on job dict | Add `if_running: skip` guard (existing APScheduler pattern) |

---

## Sources

- [Vercel: CDN origin timeout increased to 2 minutes](https://vercel.com/changelog/cdn-origin-timeout-increased-to-two-minutes)
- [Vercel: ROUTER_EXTERNAL_TARGET_ERROR](https://vercel.com/docs/errors/ROUTER_EXTERNAL_TARGET_ERROR)
- [Vercel: Function timeout limits](https://vercel.com/docs/functions/limitations)
- [Vercel: Configuring function duration](https://vercel.com/docs/functions/configuring-functions/duration)
- [Vercel: Rewrites documentation](https://vercel.com/docs/rewrites)
- [FastAPI: Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [FastAPI Discussion #8323: 202 Accepted for long-running tasks](https://github.com/fastapi/fastapi/discussions/8323)
- [FastAPI polling strategy for long-running tasks](https://openillumi.com/en/en-fastapi-long-task-progress-polling/)
- [SWR: Automatic Revalidation](https://swr.vercel.app/docs/revalidation)
- [SWR: API options (refreshInterval, refreshWhenHidden)](https://swr.vercel.app/docs/api)
- [Upstash: Get rid of Vercel function timeouts](https://upstash.com/blog/vercel-cost-workflow)
- [Inngest: How to solve Next.js timeouts](https://www.inngest.com/blog/how-to-solve-nextjs-timeouts)
- [next.js Discussion #36598: Configurable proxyTimeout for rewrites](https://github.com/vercel/next.js/discussions/36598)
