# Workday CXS API: Technical Reference

> Reverse-engineered, undocumented API powering all `*.myworkdayjobs.com` career sites. No auth required.
> Validated against: 2020 Companies (wd1), Walmart (wd5), P&G (wd5), Mastercard (wd1). Feb 2026.
> Sources: Perplexity research (live-validated), Claude research (practitioner synthesis).

## Section Index

| Section | Load when |
|---------|-----------|
| §1 Endpoints & URL Pattern | Building the Workday adapter, deriving API URLs |
| §2 Search API | Implementing pagination, filtering, request/response schema |
| §3 Detail API | Fetching full posting content, field reference |
| §4 Rate Limiting | Setting delays, concurrency, safe parameters |
| §5 Tenant Variations | Multi-tenant config, what stays consistent vs varies |
| §6 Gotchas & Edge Cases | Pagination traps, date handling, HTML parsing |
| §7 Code Pattern | Async scraper with dedup, concurrency, date parsing |

---

## §1 Endpoints & URL Pattern

```
Base:    https://{tenant}.wd{N}.myworkdayjobs.com
Search:  POST /wday/cxs/{tenant}/{site}/jobs
Detail:  GET  /wday/cxs/{tenant}/{site}/job/{externalPath}
```

For **2020 Companies**: `tenant=2020companies`, `N=1`, `site=External_Careers`

**Deriving from career page URL** — insert `/wday/cxs/{tenant}/` between domain and site:
```
Career page: https://2020companies.wd1.myworkdayjobs.com/External_Careers
Search API:  https://2020companies.wd1.myworkdayjobs.com/wday/cxs/2020companies/External_Careers/jobs
```

| Endpoint | Method | Required Headers |
|----------|--------|------------------|
| Search | **POST** | `Content-Type: application/json` (omitting → 500, not 400) |
| Detail | **GET** | `Accept: application/json` (optional but recommended) |

No API keys, CSRF tokens, cookies, or authentication required. Cloudflare sits in front (cf-ray, __cf_bm cookies observed) but doesn't block light scraping.

---

## §2 Search API

### Request Body

```json
{"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
```

| Parameter | Type | Notes |
|-----------|------|-------|
| `limit` | int | **Hard max 20.** Values >20 silently return `{"total": null, "jobPostings": []}` |
| `offset` | int | Zero-based. Negative → 400. |
| `searchText` | string | Free-text keyword search. Empty → all jobs. |
| `appliedFacets` | object | Filter by facet IDs (opaque hex strings from response `facets` array) |

### Facet Filtering

Facet IDs must be discovered from search response. Known standard facet keys: `locations`, `locationCountry`, `jobFamilyGroup`, `timeType`, `workerSubType`, `postedOn`.

**`postedOn` filter values:** `"0"` = today, `"1"` = past 7 days, `"2"` = past 30 days, omitted = all time.

### Response Schema

```json
{
  "total": 815,
  "jobPostings": [
    {
      "title": "Samsung Market Sales Manager",
      "externalPath": "/job/Carlstadt-NJ/Samsung-Market-Sales-Manager_REQ_099113",
      "locationsText": "Carlstadt, NJ",
      "postedOn": "Posted Today",
      "bulletFields": ["REQ_099113"],
      "timeType": "Full time"
    }
  ],
  "facets": [...],
  "userAuthenticated": false
}
```

| Field | Reliability | Notes |
|-------|:-----------:|-------|
| `total` | Always | Total matching jobs. `null` if request malformed (limit=0 or >20). |
| `jobPostings` | Always | Empty `[]` at end of pagination, not `null`. |
| `.title` | Always | Job title. |
| `.externalPath` | Always | Path for detail endpoint. |
| `.locationsText` | Always | Human-readable location. |
| `.postedOn` | Always | Relative: "Posted Today", "Posted 7 Days Ago", "Posted 30+ Days Ago". **Not parseable as date.** |
| `.bulletFields` | Always | Usually contains requisition ID. May have 2-4 items. |
| `.timeType` | Most | Present for 2020 Companies/Walmart/Mastercard. **Absent** for P&G. |

### Pagination

Offset-based: increment by 20 until `offset >= total` or empty `jobPostings`.

**2,000-result ceiling:** Workday caps pagination at ~2,000 results. Beyond offset 1980, `total` becomes unreliable (observed returning 0 for Walmart while still returning jobs). For tenants >2,000 jobs, **partition by `appliedFacets`** (location, category, posting date).

For 2020 Companies (~815 jobs): ~41 pages, not a concern.

---

## §3 Detail API

Construct URL: `{DETAIL_BASE}{externalPath}` — use `externalPath` from search results verbatim (handles locale prefixes).

### Response Schema

```json
{
  "jobPostingInfo": {
    "id": "0882f18309b11001afbdfc4bb41f0000",
    "title": "Samsung Market Sales Manager",
    "jobDescription": "<p>Rich HTML content...</p>",
    "location": "Carlstadt, NJ",
    "startDate": "2026-02-12",
    "timeType": "Full time",
    "jobReqId": "REQ_099113",
    "country": {"descriptor": "United States of America", "alpha2Code": "US"},
    "canApply": true,
    "externalUrl": "https://..."
  },
  "hiringOrganization": {"name": "2020 Companies, Inc.", "url": ""},
  "similarJobs": []
}
```

### Field Reference (jobPostingInfo)

| Field | Reliability | Notes |
|-------|:-----------:|-------|
| `id` | Always | Internal Workday GUID. |
| `title` | Always | Job title. |
| `jobDescription` | Always | **Full HTML** — `<p>`, `<ul>/<li>`, `<b>`, `<br/>`. Safe to parse (no JS, no img). |
| `location` | Always | Display location. |
| `startDate` | Always | **ISO 8601 date** (`YYYY-MM-DD`). The posting date. Not in search results — detail only. |
| `timeType` | Always | "Full time" or "Part time". |
| `jobReqId` | Always | Requisition ID. Format varies: `REQ_099113` (2020), `R-2416431` (Walmart). |
| `country` | Always | Object with `descriptor` and `alpha2Code`. |
| `canApply` | Always | Whether applications are open. |
| `externalUrl` | Always | Canonical URL. |
| `additionalLocations` | Optional | Array of other locations (may be empty or absent). |
| `remote` | Optional | Boolean remote flag (absent on many tenants). |
| `jobFamilyGroup` | Optional | Array of `{descriptor: "..."}` objects. Job categories. |
| `endDate` | Optional | ISO date. Present for time-bound postings (internships). |

**`hiringOrganization.name`** may differ from brand (e.g., Walmart returns "Sam's West, Inc." for Sam's Club jobs). `.url` is consistently empty.

---

## §4 Rate Limiting

No published limits. No rate-limit headers. No auth required. Workday uses infrastructure-level protection (Cloudflare + internal).

### Safe Parameters for Daily Scraping (single tenant)

| Parameter | Value |
|-----------|-------|
| Delay between search pages | 1-1.5 seconds (sequential) |
| Detail fetch concurrency | 5 parallel with semaphore |
| Delay between detail fetches | 0.5-1 second |
| User-Agent | Standard browser string |
| Cookies/session | Not required (fully stateless) |

**For 2020 Companies (~815 jobs):** ~41 search pages + 815 details ≈ **14 min at 1 req/sec** (sequential) or **~8 min** with semaphore concurrency.

**IP blocking:** Not observed at low volume. Expected at sustained high volume. Exponential backoff on 403/429. For multi-tenant, run sequentially across domains (rate limits are per-domain).

---

## §5 Tenant Variations

### Consistent Across All Tenants

URL pattern, request body schema, max page size 20, response structure (`total`, `jobPostings`, `facets`), detail structure (`jobPostingInfo` wrapper), HTML descriptions, relative date strings.

### What Varies

| Element | Details |
|---------|---------|
| `wd{N}` instance | `wd1`, `wd3`, `wd5`, `wd12` — must match exactly, permanent per company |
| Site name | `External_Careers`, `CorporateCareers`, `WalmartExternal` — fully custom |
| Req ID format | `REQ_099113` (2020), `R-2416431` (Walmart), `R000145661` (P&G) |
| `timeType` in search | Present most tenants. Absent for P&G. |
| Available facets | Standard facets everywhere; some tenants add custom `cf-REC-*` facets |
| Locale in paths | Some: `/en-US/job/...`, others: `/job/...` — use `externalPath` verbatim |
| Domain variant | Minority use `myworkdaysite.com` instead of `myworkdayjobs.com` |

**Adapting to another company** — change 3 variables: `TENANT`, `WD_INSTANCE`, `SITE`. All derivable from career page URL.

---

## §6 Gotchas & Edge Cases

**Pagination traps:**
- `limit > 20` → silently returns `{"total": null, "jobPostings": []}`. No error. #1 gotcha.
- `limit = 0` → same silent failure.
- Offset-based pagination → jobs shift mid-scrape. Deduplicate by `externalPath`.

**Date handling:**
- `postedOn` is relative strings only ("Posted 30+ Days Ago" = 31 or 365 days, no precision)
- `startDate` (detail only) is ISO 8601, the actual posting date — **use this for CompGraph's `first_seen_at`**
- No "posted after" API filter exists. Use `postedOn` facet ("0"/"1"/"2") for coarse filtering.

**HTML descriptions:**
- HTML entities: `&#39;`, `&#43;`, `&#34;` → decode
- Empty `<p style="text-align:inherit"></p>` spacers → strip
- Non-breaking spaces `\u00a0` throughout
- Well-formed HTML, no missing closing tags, no JS

**Disappearing jobs:** Postings can be removed between search and detail fetch. Handle 404s gracefully. `canApply: false` may appear for closed but indexed postings.

**Content-Type omission:** Returns HTTP 500 (not 400) with HTML error body.

---

## §7 Code Pattern

### Daily Delta Strategy (efficient)

1. Paginate search → collect all `externalPath` + `bulletFields` (req IDs)
2. Compare req IDs against previous run's stored set
3. Fetch detail **only for new** req IDs
4. Reduces daily detail fetches from ~815 to just new postings

### Relative Date Parser

```python
import re
from datetime import date, timedelta

def parse_posted_on(posted_on: str) -> date | None:
    s = posted_on.lower().strip()
    today = date.today()
    if "today" in s: return today
    if "yesterday" in s: return today - timedelta(days=1)
    m = re.search(r"(\d+)\+?\s*days?\s*ago", s)
    return today - timedelta(days=int(m.group(1))) if m else None
```

### Core API Calls

```python
# Search (paginate)
async def search_page(client: httpx.AsyncClient, offset: int = 0) -> tuple[int, list[dict]]:
    resp = await client.post(SEARCH_URL, json={
        "appliedFacets": {}, "limit": 20, "offset": offset, "searchText": ""
    })
    data = resp.json()
    return data.get("total", 0), data.get("jobPostings", [])

# Detail
async def fetch_detail(client: httpx.AsyncClient, external_path: str) -> dict:
    resp = await client.get(f"{DETAIL_BASE}{external_path}")
    return resp.json()
```

### Multi-Tenant Config

```python
TARGETS = [
    {"tenant": "2020companies", "wd": "wd1", "site": "External_Careers"},
    # Add competitors as discovered
]
```

**Velocity shortcut:** A single search POST with `limit=1` returns `total` — the active posting count. No full scrape needed for daily hiring velocity signal.
