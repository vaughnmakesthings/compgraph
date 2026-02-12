# iCIMS Career Portal Scraping: Technical Reference

> Reverse-engineered iCIMS career portal scraping patterns for Classic ATS portals.
> Targets: BDS Connected Solutions (`careers-bdssolutions.icims.com`), MarketSource (`applyatmarketsource-msc.icims.com`).
> Validated: Feb 2026. Sources: Perplexity research (live-validated), Claude research (practitioner synthesis).

## Section Index

| Section | Load when |
|---------|-----------|
| §1 Portal Architecture | Understanding iframe bypass, portal types, URL patterns |
| §2 Search & Pagination | Implementing search pagination, detecting last page |
| §3 Detail & JSON-LD | Extracting structured job data from detail pages |
| §4 Anti-Scraping & Rate Limits | Request config, safe parameters, CDN behavior |
| §5 Gotchas & Edge Cases | Iframe trap, portal decommissioning, CSS fragility |
| §6 Code Pattern | Two-phase scraper, search parsing, JSON-LD extraction |

---

## UNRESOLVED CONFLICTS — Validate Before Implementation

This document was merged from two research sources that **contradict each other** on critical implementation questions. The Perplexity source was live-validated; the Claude source synthesized practitioner accounts. Neither source is definitively authoritative on the disputed points below. **The implementing agent MUST run the validation steps before writing adapter code.**

### UC-1: Does plain HTTP + `?in_iframe=1` return usable HTML?

| Source | Claim |
|--------|-------|
| Perplexity (live-validated) | Yes — fully server-rendered HTML, no JS required. Scraped 168 BDS jobs + 400 MarketSource jobs with httpx. |
| Claude (practitioner synthesis) | No — iCIMS portals are JavaScript SPAs. Plain HTTP returns empty HTML shells. Playwright required. |

**Why it matters:** This determines the entire scraper architecture — httpx+BeautifulSoup (fast, lightweight) vs Playwright (slow, heavy, browser dependency).

**This document assumes Perplexity is correct** (plain HTTP works for Classic portals). If validation fails, fall back to Playwright architecture from Claude's report.

**Validation:**
```bash
curl -s "https://careers-bdssolutions.icims.com/jobs/search?ss=1&in_iframe=1" | grep -c "iCIMS_JobsTable"
# Expected if Perplexity correct: >= 1 (HTML contains job data)
# Expected if Claude correct: 0 (empty shell, no job data)
```

### UC-2: Is JSON-LD present in server HTML or only after JS execution?

| Source | Claim |
|--------|-------|
| Perplexity | Present in initial server HTML — extractable with regex on raw HTTP response. |
| Claude | Injected by JavaScript — only present after browser renders the page. |

**Why it matters:** If JSON-LD requires JS, detail page extraction also needs Playwright. If server-side, httpx works end-to-end.

**Validation:**
```bash
# Pick any active job ID from BDS (check search results first)
curl -s "https://careers-bdssolutions.icims.com/jobs/47906/job?in_iframe=1" | grep -c "application/ld+json"
# Expected if Perplexity correct: >= 1
# Expected if Claude correct: 0
```

### UC-3: Is MarketSource portal live or decommissioned?

| Source | Claim |
|--------|-------|
| Perplexity | Live at `applyatmarketsource-msc.icims.com`, ~400 jobs, 20/page. |
| Claude | Decommissioned (HTTP 410). MarketSource migrated to BrassRing (`sjobs.brassring.com`). Customer ID 14529. |

**Why it matters:** If decommissioned, the MarketSource adapter target URL changes entirely and may require a different ATS scraper (BrassRing ≠ iCIMS).

**Validation:**
```bash
curl -s -o /dev/null -w "%{http_code}" "https://applyatmarketsource-msc.icims.com/jobs/search?ss=1&in_iframe=1"
# Expected if Perplexity correct: 200
# Expected if Claude correct: 410 or 301/302 redirect
```

If 410 or redirect, check alternative:
```bash
curl -s -o /dev/null -w "%{http_code}" "https://careers-marketsource.icims.com/jobs/search?ss=1&in_iframe=1"
```

---

## §1 Portal Architecture

iCIMS Classic portals use a **two-layer iframe architecture**. The outer page serves a branding wrapper; actual job content loads inside `<iframe id="icims_content_iframe">`.

**The bypass:** append `?in_iframe=1` to any URL. iCIMS returns the inner-frame HTML directly as a standalone page — **fully server-rendered, no JavaScript required** for Classic portals. The iCIMS codebase confirms this with `icims_stripIFrameParameter()`.

### Two Portal Types

| Type | Stack | HTTP scraping | Example |
|------|-------|:---:|---------|
| **Classic** (iCIMS Recruit) | Server-rendered iframe | Works with `?in_iframe=1` | `careers-bdssolutions.icims.com` |
| **Modern Career Sites** (Jibe/Attract) | React SPA, `cms.jibecdn.com` | Requires Playwright | Custom domains, AI chatbots |

**CompGraph targets use Classic portals.** If a future target uses Modern Career Sites, switch to Playwright with `networkidle` wait.

### URL Patterns (All Classic Portals)

| Resource | URL Pattern |
|----------|-------------|
| Search (page 1) | `https://{subdomain}.icims.com/jobs/search?ss=1&in_iframe=1` |
| Search (page N) | `…/jobs/search?ss=1&in_iframe=1&searchRelation=keyword_all&pr={N}` |
| Job detail | `https://{subdomain}.icims.com/jobs/{jobId}/job?in_iframe=1` |

The slug in detail URLs is **cosmetic** — `/jobs/{id}/wrong-slug/job` returns the same content as `/jobs/{id}/job`. Use the slug-free form.

### Portal Status (Verify Before Implementation)

| Portal | Subdomain | Status (Feb 2026) |
|--------|-----------|-------------------|
| BDS Connected Solutions | `careers-bdssolutions` | Live, Classic portal, ~168 jobs |
| MarketSource | `applyatmarketsource-msc` | **Conflicting reports** — one source found ~400 jobs; another reports HTTP 410 (decommissioned, migrated to BrassRing). **Verify live before building adapter.** |
| MarketSource (alt) | `careers-marketsource` | May redirect to `sjobs.brassring.com` (different ATS) |

---

## §2 Search & Pagination

Pagination uses the `pr=` parameter, **zero-indexed** (pr=0 = page 1, pr=1 = page 2). Plain server-side rendering with full page reloads — no AJAX or cursor pagination.

### Page Sizes (Company-Configured)

| Portal | Jobs/Page | Total Pages | Total Jobs |
|--------|:---------:|:-----------:|:----------:|
| BDS Connected Solutions | 50 | 4 | ~168 |
| MarketSource | 20 | 20 | ~400 |

**Do not hardcode page size.** Detect dynamically — companies can change portal configuration.

### Detecting Total Pages

1. **"Page X of Y" text** (most reliable): `<h2 class="iCIMS_SubHeader iCIMS_SubHeader_Jobs">Search Results Page X of Y</h2>` — parse with `r"Page\s+\d+\s+of\s+(\d+)"`
2. **`<link rel="next">`**: Present in `<head>` on all pages except the last — its absence signals the final page
3. **Pagination nav**: `<div class="iCIMS_PagingBatch">` — current page has `class="selected"`

### Search Filter Parameters

| Parameter | Purpose |
|-----------|---------|
| `searchKeyword` | Free-text keyword search |
| `searchCategory` | Category filter (company-defined numeric IDs) |
| `searchPositionType` | Full-time / Part-time |
| `searchLocation` | Location filter (free text) |
| `searchRadius` / `searchZip` | Geo radius search |
| `searchRelation` | `keyword_all` (AND) or `keyword_any` (OR) |

### Search Page HTML Selectors

| Field | Selector |
|-------|----------|
| Job table container | `div.container-fluid.iCIMS_JobsTable` |
| Individual job row | `div.row` (direct child of table) |
| Title + link | `div.col-xs-12.title > a.iCIMS_Anchor > h3` |
| Job ID | From href: `/jobs/{id}/` |
| Description snippet | `div.col-xs-12.description` |
| Metadata tags | `div.col-xs-12.additionalFields > dl.iCIMS_JobHeaderGroup` |
| Category/Location/Pay | `dt.iCIMS_JobHeaderField` label → sibling `dd.iCIMS_JobHeaderData` |

Available metadata fields vary by portal — BDS shows Category, Location, Position Type, Maximum Pay. MarketSource shows ID and Category. Structure is always `dl > div.iCIMS_JobHeaderTag > dt + dd`.

---

## §3 Detail & JSON-LD

Every Classic iCIMS detail page embeds a `<script type="application/ld+json">` block containing Schema.org `JobPosting`. **This is the recommended extraction method** — structured JSON that survives portal redesigns.

### JSON-LD Schema (Consistent Across Portals)

```json
{
  "@context": "http://schema.org",
  "@type": "JobPosting",
  "title": "Snapdragon Market Development Manager",
  "description": "<h2>At a Glance</h2><p>...",
  "datePosted": "2026-02-11T05:00:00.000Z",
  "validThrough": "2027-02-11T05:00:00.000Z",
  "employmentType": "FULL_TIME",
  "occupationalCategory": "Training/Market Representation",
  "directApply": true,
  "url": "https://careers-bdssolutions.icims.com/jobs/47906/...",
  "hiringOrganization": {"name": "BDS Connected Solutions, LLC.", "sameAs": "https://www.bdssolutions.com/"},
  "jobLocation": [{"address": {"addressLocality": "West Hollywood", "addressRegion": "CA", "postalCode": "90069", "addressCountry": "US"}}]
}
```

| Field | Reliability | CompGraph Mapping |
|-------|:-----------:|-------------------|
| `title` | Always | `postings.title` |
| `description` | Always | Full HTML (3K–8K chars) → enrichment input |
| `datePosted` | Always | ISO 8601 → `postings.first_seen_at` |
| `validThrough` | Always | Expiration date |
| `employmentType` | Always | `FULL_TIME` / `PART_TIME` |
| `occupationalCategory` | Always | Category string |
| `hiringOrganization.name` | Always | `companies.name` (may differ from brand) |
| `jobLocation[].address` | Always | City, state, zip, country |
| `directApply` | Always | Boolean |
| `url` | Always | Canonical URL |

**Expired/filled jobs return HTTP 410 (Gone)**, not 404. Handle gracefully — detect stale listings.

---

## §4 Anti-Scraping & Rate Limits

iCIMS Classic portals are **remarkably scraper-friendly** for plain HTTP requests.

### What They Don't Enforce

- No User-Agent validation (works with `python-httpx/0.27.0`, curl default, even empty UA)
- No cookie/session requirements — fully stateless GET requests
- No CAPTCHA on search or detail pages
- No JavaScript challenge pages
- No referrer checking
- No rate-limit headers on portal frontend

### What Exists But Doesn't Block

- **CloudFront CDN** (`x-cache`, `x-amz-cf-*` headers) — caching layer, no aggressive bot detection
- **Fastly** on some deployments (varies by company)
- `JSESSIONID` cookies set but not required
- `Cache-Control: no-cache, no-store` — always hitting origin

### Historical: June 2022 Headless Browser Blocking

iCIMS began returning 502 errors to headless rendering engines (Splash). Workaround: use `?in_iframe=1` with plain HTTP + JSON-LD extraction. This remains the recommended approach.

### Safe Parameters for Daily Scraping

| Parameter | Value |
|-----------|-------|
| Delay between requests | 0.5 seconds |
| Detail fetch concurrency | 5 parallel (semaphore) |
| User-Agent | Standard browser string |
| Cookies/session | Not required |

**For BDS + MarketSource (~568 jobs):** Full scrape including detail pages completes in under 10 minutes at these rates.

### Authenticated API (If Ever Available)

REST API at `api.icims.com` requires Basic Auth. Rate limit: 10,000 calls/day. Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`. Not relevant unless partner credentials obtained. BDS customer ID: `10405` (from `icims-ats-customer` header).

---

## §5 Gotchas & Edge Cases

1. **The iframe trap (#1 gotcha):** Scraping without `?in_iframe=1` returns an empty branding wrapper with zero job data. Always include this parameter.

2. **Portal decommissioning:** Companies migrate between iCIMS products or to other ATS platforms without notice. MarketSource may have migrated from Classic to BrassRing. Monitor for HTTP 410 responses and have fallback discovery.

3. **CSS selector fragility:** iCIMS's iBrand customization lets each company wrap the portal in their own design. JSON-LD extraction is far more stable than CSS selectors across portals.

4. **HTML entity encoding:** Descriptions contain `&nbsp;`, `&rsquo;`, `&ndash;`. BeautifulSoup handles automatically; regex on raw HTML needs entity decoding first.

5. **Inline style soup:** Detail HTML has deeply nested `<span>` tags with inline styles (Word copy-paste). JSON-LD `description` is cleaner but still HTML.

6. **Variable page sizes:** Don't assume 20 or 50 — always parse "Page X of Y" dynamically.

7. **No-cache headers:** Always hitting origin. Be respectful with frequency.

8. **Job ID uniqueness:** iCIMS IDs are sequential integers. Use `(portal_subdomain, job_id)` tuple as unique key — different companies could share IDs.

9. **Transient 502 errors:** Occasional during maintenance. Implement retry with exponential backoff (3 attempts).

10. **Geolocation parameters:** `latitude`, `longitude`, `jan1offset`, `jun1offset` injected by JS. Safely omit them — `?ss=1&in_iframe=1` returns all jobs.

11. **Redirect parameters:** `hashed=0&needsRedirect=false` may help prevent server-side redirects on some portals.

12. **No sitemaps:** iCIMS portals don't expose `sitemap.xml`. Job discovery must go through search pages.

---

## §6 Code Pattern

### Two-Phase Approach

1. **Search phase:** Paginate search pages → collect job IDs, titles, locations, metadata from HTML
2. **Detail phase:** Fetch detail pages → extract JSON-LD for structured data (datePosted, full description, organization, location)

Skip Phase 2 if you only need listing-level data (e.g., velocity counting).

### Search Page Parser

```python
import re
from bs4 import BeautifulSoup

def parse_search_page(html: str) -> tuple[list[dict], int]:
    """Returns (jobs, total_pages)."""
    soup = BeautifulSoup(html, "lxml")
    total_pages = 1
    header = soup.find("h2", class_="iCIMS_SubHeader_Jobs")
    if header:
        m = re.search(r"Page\s+\d+\s+of\s+(\d+)", header.get_text())
        if m:
            total_pages = int(m.group(1))

    jobs = []
    table = soup.find("div", class_="iCIMS_JobsTable")
    if not table:
        return jobs, total_pages

    for row in table.find_all("div", class_="row", recursive=False):
        anchor = row.select_one("div.title a.iCIMS_Anchor")
        if not anchor:
            continue
        href = anchor.get("href", "")
        id_match = re.search(r"/jobs/(\d+)/", href)
        if not id_match:
            continue
        jobs.append({"job_id": id_match.group(1), "title": anchor.get_text(strip=True), "href": href})
    return jobs, total_pages
```

### JSON-LD Extractor

```python
import json, re

def extract_jsonld(html: str) -> dict:
    """Extract Schema.org JobPosting from detail page."""
    match = re.search(r'<script\s+type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return {}
```

### Multi-Portal Config

```python
PORTALS = {
    "bds": "https://careers-bdssolutions.icims.com",
    "marketsource": "https://applyatmarketsource-msc.icims.com",  # verify status
}
```

### Response Headers Worth Monitoring

| Header | Example | Use |
|--------|---------|-----|
| `x-icims-build` | `179.0.0` | Detect platform version changes |
| `x-icims-cid` | `prod_bdsmktg` | Company identifier |
| `icims-ats-customer` | `10405` | Numeric customer ID |
| `x-cache` | `Miss from cloudfront` | CDN cache status |
