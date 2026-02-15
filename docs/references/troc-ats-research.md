# T-ROC ATS Research

**Date:** February 15, 2026
**Status:** Complete — Workday CXS confirmed, no new adapter needed

## ATS Platform Identification

T-ROC uses **Workday CXS** for job postings, hosted on Workday's `wd501` data center.

### Discovery Path

1. **WordPress frontend** at `jobs.trocglobal.com` — a marketing landing page, not the ATS itself
2. Job listing links redirect to `troc.wd501.myworkdayjobs.com/TROC_External/`
3. Standard Workday CXS API confirmed at the expected endpoint

### Legacy/Secondary ATS

A legacy iCIMS portal exists at `careers-troc.icims.com`, but it appears to be secondary or deprecated. The primary career site links exclusively to the Workday instance.

## Workday CXS Configuration

| Field | Value |
|-------|-------|
| Tenant | `troc` |
| Site | `TROC_External` |
| Data center | `wd501` |
| Search endpoint | `https://troc.wd501.myworkdayjobs.com/wday/cxs/troc/TROC_External/jobs` |
| Detail endpoint | `https://troc.wd501.myworkdayjobs.com/wday/cxs/troc/TROC_External/jobs/{job_id}` |
| Career site URL | `https://troc.wd501.myworkdayjobs.com` |

## API Behavior

- **Pagination:** Standard Workday CXS offset/limit (20 per page)
- **Total jobs:** ~565 at time of inspection
- **Response format:** Standard Workday CXS JSON (identical structure to Advantage Solutions and Acosta Group)
- **Rate limiting:** No special anti-bot measures observed beyond standard Workday CXS behavior

## Chatbot

A Paradox AI chatbot ("Olivia") is present on the WordPress frontend. It does not affect the Workday CXS API and is irrelevant to scraping.

## Implementation Decision

The existing `WorkdayAdapter` in `src/compgraph/scrapers/workday.py` handles tenant/site configuration via the `Company.scraper_config` JSONB field. T-ROC requires **zero new adapter code** — only a new company row with the correct config:

```python
Company(
    name="T-ROC",
    slug="troc",
    ats_platform="workday",
    career_site_url="https://troc.wd501.myworkdayjobs.com",
    scraper_config={"tenant": "troc", "site": "TROC_External"},
)
```

This matches the pattern used by Advantage Solutions and Acosta Group.

## Data Center Note

T-ROC uses `wd501` while Advantage Solutions and Acosta Group use `wd1`. The data center subdomain is part of `career_site_url` and handled automatically by the adapter's URL construction logic.
