# Scrape Run Observation Report

**Date:** 2026-02-17, 10:00 PM EST (03:00 UTC Feb 18)
**Observer:** Claude (automated monitoring via Chrome + API + SSH logs)
**Environment:** Raspberry Pi dev server (`100.102.42.5`) running `main` at commit `4f2d3e0`
**Trigger:** Manual `POST /api/scrape/trigger` via VPN

---

## Executive Summary

A full scrape run was triggered and monitored end-to-end across all 5 dashboard pages, the REST API, and server logs. The pipeline successfully scraped 1,025 postings from all 4 competitor companies with zero errors in ~11.5 minutes. The dashboard broadly reflects intended behavior during and after the run, with live metric updates, correct state transitions, and proper control button behavior. Four issues were identified — one high-severity bug (BDS location data stored as raw JSON), one medium-severity state synchronization gap, and two low-severity UX confusers. No data corruption, crashes, or enrichment pipeline regressions were observed.

---

## Timeline

| Time (UTC) | Event |
|------------|-------|
| 03:00:19 | Scrape triggered, 4 companies start |
| 03:01:30 | T-ROC completes (93 postings, 0 new snapshots, 15 deactivated) |
| 03:02:37 | MarketSource completes (24 postings, 24 new snapshots) |
| 03:09:58 | BDS completes (100 postings, 100 new snapshots) |
| 03:11:54 | 2020 Companies completes (808 postings, 0 new snapshots) |
| 03:11:56 | Pipeline status transitions to SUCCESS |

**Total:** 1,025 postings found, 124 new snapshots created, 0 errors, 4/4 companies succeeded.

---

## Baseline (Pre-Scrape)

Before triggering the run, the dashboard showed a healthy idle state:

- **System state:** Idle (green banner)
- **Last scrape/enrich:** Both completed ~1 hour prior
- **Data freshness:** All 4 companies green (scraped within 24h)
- **Enrichment coverage:** 932 total active, 932 enriched, 0 unenriched
- **Scheduler:** Enabled, next run at 02:00 EST (07:00 UTC)

The system was clean — no orphan runs, no stale state.

---

## Page-by-Page Observations

### Main Dashboard (`/`)

**During scrape:** After a manual refresh (auto-refresh was off — see Issue #99), the page correctly showed:
- Blue info banner: "Scraping... (0m 56s)" with live elapsed timer
- Scrape card: Status RUNNING (blue), Postings Found metric, Companies Done counter
- Enrichment card: unchanged (COMPLETED, 1h ago)
- Auto-refresh activated at 5-second intervals once active state detected

**Post-scrape:** Clean transition to:
- Green banner: "System Idle"
- Scrape: SUCCESS (green), "Completed 1m ago"
- All 4 freshness timestamps updated to this run's completion times
- Enrichment coverage updated: 1025 total active, 901 enriched, 124 unenriched

**Verdict:** Working as intended, minus the auto-refresh gap (#99).

### Pipeline Health (`/Pipeline_Health`)

**During scrape:** The page showed a mixed view of active and historical data:
- T-ROC freshness updated immediately upon completion (03:01 UTC)
- Recent Scrape Runs table showed both the active run's per-company rows and prior completed runs
- Active companies displayed "Running (1m elapsed)" in the `completed_at` column — nice UX touch
- Enrichment coverage reflected real-time deactivation (932 → 917 active after T-ROC closed 15 postings)

**Issues observed:**
- Company `scrape_status` column showed "pending" for actively running companies (see #97)
- Enrichment pass breakdown remained stable throughout (no regression)

**Verdict:** Informative and mostly correct, but the "pending" vs "running" state discrepancy is confusing.

### Posting Explorer (`/Posting_Explorer`)

**During scrape:** Accessible and responsive. Data freshness indicator showed current timestamp. Filters (Company, Status, Role Archetype, Enrichment) all functional.

**Post-scrape:** BDS postings appeared with raw JSON in the location column — structured iCIMS address objects displayed as Python dict strings instead of parsed location strings like "Houston, TX" (see #98). New BDS/MarketSource postings correctly showed `role_archetype: None` since they haven't been enriched yet.

**Verdict:** Functional, but the BDS location bug is a high-severity data quality issue that needs fixing before the data collection period produces meaningful results.

### Pipeline Controls (`/Pipeline_Controls`)

**During scrape:** This is the operational command center and it performed well:
- Status: RUNNING (blue) with live metrics updating via 3-second auto-refresh
- Per-Company Progress table with state icons (hourglass for pending, green check for completed)
- Start Scrape button correctly disabled, Pause/Stop/Force Stop enabled
- Metrics tracked accurately: postings, snapshots, succeeded count, errors

**Post-scrape:**
- Status: SUCCESS (green)
- All 4 companies showed completed state with correct per-company metrics
- Start Scrape re-enabled, Pause hidden, Stop/Force Stop disabled
- Auto-refresh stopped (correct — terminal state)

**Verdict:** Best-performing page. The real-time control panel works as designed. Same "pending vs running" state issue as Pipeline Health (#97).

### Scheduler (`/Scheduler`)

- Schedule displayed correctly: `daily_pipeline — SCHEDULED`, next run at 02:00 local
- Trigger Now / Pause / Resume controls present and functional
- "Last Run: Never" and "No pipeline runs recorded yet" — technically correct (this run was API-triggered, not scheduler-triggered) but confusing (#100)

**Verdict:** Functional for its purpose, but the disconnect between "scheduler runs" and "all pipeline runs" is a UX gap.

---

## Scraper Performance

| Company | ATS | Postings | New Snapshots | Deactivated | Duration | Notes |
|---------|-----|----------|---------------|-------------|----------|-------|
| T-ROC | Workday CXS | 93 | 0 | 15 | 1m 10s | Fast. All postings existed. 15 correctly deactivated. |
| MarketSource | iCIMS | 24 | 24 | 0 | 2m 15s | All snapshots new (data changed since last run). |
| BDS | iCIMS | 100 | 100 | 0 | 9m 40s | Slow — iCIMS page-by-page fetching. All snapshots new. |
| 2020 Companies | Workday CXS | 808 | 0 | 0 | 11m 30s | Largest catalog. All postings existed, no changes. |

**Key observations:**
- Workday CXS scrapers are significantly faster than iCIMS (API vs page scraping)
- iCIMS scrapers (BDS, 2020) spent extended periods with 0 reported results before completing in bulk — progress is not incremental, it's batched at the end
- T-ROC deactivation detection is working correctly (15 postings closed)
- 2020 Companies has by far the largest catalog (808 postings) but produced 0 new snapshots — stable data

---

## Infrastructure

- **Server resources:** Pi handling the load comfortably (547Mi/7.7Gi RAM, load 0.26 during scrape)
- **Network:** Single outbound HTTPS connection at a time from uvicorn (sequential within each scraper)
- **Database:** 4 PostgreSQL pooler connections maintained throughout
- **Logging gap:** Only HTTP access logs visible at INFO level. No scraper progress, page counts, or timing breakdowns logged. This makes diagnosing slow scrapers difficult without adding debug logging.

---

## Post-Run State

After scrape completion:
- **Enrichment did not auto-trigger.** The manual `POST /api/scrape/trigger` endpoint only runs the scrape phase. The full scrape → enrich → aggregate pipeline only runs when triggered by the scheduler's cron job or the "Trigger Now" button on the Scheduler/Main pages.
- **124 postings are unenriched** (100 BDS + 24 MarketSource new snapshots). These will be enriched on the next scheduled pipeline run (02:00 EST).
- **System state:** Idle, healthy, ready for next run.

---

## Issues Filed

| Issue | Severity | Title |
|-------|----------|-------|
| [#97](https://github.com/vaughnmakesthings/compgraph/issues/97) | Medium | Dashboard shows "pending" for companies that are actively running |
| [#98](https://github.com/vaughnmakesthings/compgraph/issues/98) | High | BDS postings display raw JSON in location column |
| [#99](https://github.com/vaughnmakesthings/compgraph/issues/99) | Low | Dashboard auto-refresh doesn't activate when scrape starts externally |
| [#100](https://github.com/vaughnmakesthings/compgraph/issues/100) | Low | Scheduler page shows "No pipeline runs" despite completed runs |

---

## Recommendations

1. **Fix BDS location parsing (#98) before the M3 data collection period** — this is the only issue that affects data quality. All other issues are UX.
2. **Add scraper progress logging at INFO level** — page counts, per-company timing, and HTTP request counts would make operational monitoring much easier.
3. **Consider always-on lightweight polling for the main dashboard** — even 30-second polling would eliminate the "frozen idle" problem (#99) without significant load.
4. **The "pending vs running" state gap (#97) is the most visible UX issue** — users watching the dashboard during a scrape will see confusing state. Worth fixing for M3.
