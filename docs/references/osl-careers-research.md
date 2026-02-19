# Research: OSL Careers Site — ATS Platform & Scraper Approach

**Date:** 2026-02-19
**Researcher:** Claude (automated browser inspection)

## Research Question

What ATS platform does OSL's careers page (oslcareers.com) use, and what scraping approach should we implement for CompGraph?

## Key Findings

### 1. OSL uses iCIMS as their backend ATS

- **Apply links** on the WordPress frontend point to `https://uscareers-oslrs.icims.com/jobs/{jobid}/job`
- The job detail page HTML contains iCIMS CSS class names: `iCIMS_JobHeaderGroup`, `iCIMS_JobHeaderField`, `iCIMS_JobHeaderData`
- The standard iCIMS search endpoint is fully functional: `https://uscareers-oslrs.icims.com/jobs/search?ss=1&searchRelation=keyword_all`

### 2. oslcareers.com is a WordPress frontend wrapper

- **Platform:** WordPress with WP Rocket 3.20.3 caching
- **Custom plugin:** `wp-content/plugins/osl-jobs/` — renders job listings from iCIMS data
- **Theme:** Custom `oslcareers` WordPress theme
- **Rendering:** Server-side rendered HTML — no client-side AJAX for job data
- The WordPress frontend is a cosmetic layer; all job data originates from iCIMS

### 3. Job data structure

**Listing page** (WordPress frontend — `oslcareers.com/browse-jobs/`):
- 604 total results, 20 per page, 7 pages
- Each card: title, job code suffix, location (city/state/country), category icon
- Search form: `GET /browse-jobs/` with params `search_query`, `location`, `lang`, `category`, `position`, `country`, `radius`

**Listing page** (iCIMS backend — `uscareers-oslrs.icims.com/jobs/search`):
- ~600 results, ~15 per page, 40 pages
- Each card: title with requisition ID, location codes (US-GA-VALDOSTA format), description preview, posted date, job ID badge
- Filters: Category, Position Type, Location

**Detail page** (both frontends expose):
- **ID:** `2026-92451` format (year-prefixed)
- **Category:** Wireless / Sans-Fil, Field Sales, Corporate, Retail, Electronics, Associate
- **Position Type:** Field Team, etc. (bilingual EN/FR labels)
- **Full description:** Rich HTML with sections (responsibilities, requirements, compensation, benefits)
- **Pay data:** Embedded in description body (e.g., "$45K-$55K per year")
- **Location:** City, State, Country

### 4. Job categories observed

| Category | Description |
|----------|------------|
| Wireless / Sans-Fil | Wireless retail sales (majority of postings) |
| Field Sales & Marketing | Field sales and marketing roles |
| Corporate : Entreprise | Corporate/HQ positions |
| Retail | Retail associate positions |
| Electronics / Électroniques | Electronics sales |
| Associate | Entry-level/associate positions |

### 5. About OSL

- **Full name:** OSL Retail Services (oslrs.com is their corporate site)
- **Business:** Outsourced sales services for North America's Fortune 500 companies
- **Focus:** Wireless retail (Walmart kiosks, carrier stores), field sales, electronics
- **Geography:** USA and Canada (bilingual EN/FR site)
- **Scale:** 604 active postings — significant hiring volume
- **Retail partners mentioned:** Walmart (wireless kiosks)
- **Competitor relevance:** Direct competitor in field marketing/outsourced sales services

## Relevance to CompGraph

### Perfect fit for existing infrastructure

OSL uses iCIMS — the same ATS platform already scraped for **MarketSource** and **BDS** in CompGraph. The iCIMS scraper (`src/compgraph/scrapers/icims.py`) is the most mature adapter in the codebase, handling:

- Paginated search listing parsing
- Job detail page fetching with circuit breaker
- Multi-portal support (multiple iCIMS subdomains per company)
- Proxy rotation and user-agent randomization

### No new scraper adapter needed

Adding OSL requires **zero new scraper code**. The implementation is purely a data/configuration task:

1. Insert OSL into the `companies` dimension table with `ats_platform = "iCIMS"` and `career_site_url = "https://uscareers-oslrs.icims.com"`
2. The existing iCIMS adapter will handle listing, pagination, and detail scraping automatically

### OSL has THREE separate iCIMS portals

| Portal | Subdomain | Language | Postings | Geography |
|--------|-----------|----------|----------|-----------|
| US | `uscareers-oslrs.icims.com` | English | ~600 (40 pages) | US only |
| Canada EN | `canadaengcareers-oslrs.icims.com` | English | ~100 (7 pages) | ON, BC, NB, AB, etc. |
| Canada FR | `canadafrcareers-oslrs.icims.com` | French | ~45 (3 pages) | QC (French Canada) |

**Important:** The Canada EN and Canada FR portals likely contain overlapping job IDs for bilingual regions. Scraping only the EN portals (US + Canada EN) avoids French-language duplicate processing while capturing all unique postings. The FR portal is primarily Quebec-only postings that may also appear in EN on the Canada EN portal.

**Portals that do NOT exist** (confirmed 404): `cacareers-oslrs`, `careers-oslrs`, `canadaencareers-oslrs`, `canadacareers-oslrs`.

### Key differences from existing iCIMS targets

| Aspect | MarketSource/BDS | OSL |
|--------|-----------------|-----|
| iCIMS subdomains | `careers-marketsource` / varies | 3 portals (see above) |
| Scale | ~200-400 postings | ~750 total across portals |
| Categories | Varies | 6 categories (Wireless dominant) |
| Geography | US only | US + Canada (bilingual, multi-portal) |
| Job IDs | Standard iCIMS numeric | Standard iCIMS numeric |
| Pay data | In description body | In description body |

## Recommended Actions

- [ ] **Add OSL company record** to `companies` table:
  ```sql
  INSERT INTO companies (id, name, slug, ats_platform, career_site_url, is_active, created_at, updated_at)
  VALUES (gen_random_uuid(), 'OSL Retail Services', 'osl', 'iCIMS',
          'https://uscareers-oslrs.icims.com', true, now(), now());
  ```
- [ ] **Run a test scrape** against OSL's iCIMS endpoint to validate parsing:
  ```bash
  # Trigger scrape for OSL only via the pipeline API
  curl -X POST http://localhost:8000/api/v1/pipeline/scrape -d '{"company_slugs": ["osl"]}'
  ```
- [ ] **Validate enrichment** on OSL postings — pay data is in description body (same pattern as existing companies), so the enrichment pipeline should work without changes
- [ ] **Monitor for edge cases:**
  - Bilingual postings (EN/FR titles and descriptions) — verify LLM enrichment handles French content
  - The `2026-XXXXX` ID format may differ from other iCIMS tenants — verify the existing `job_id` extraction handles this
  - Some postings span multiple locations (e.g., "US-GA-VALDOSTA | US-GA-THOMASVILLE") — verify multi-location parsing
- [ ] **Optional: WordPress frontend fallback** — if iCIMS ever blocks direct access, `oslcareers.com/browse-jobs/` can serve as an alternative data source with GET-based pagination. This would require a new lightweight HTML scraper but the same data is available.

## Open Questions (Updated)

- ~~**Canadian postings**: Are they on a separate portal?~~ **RESOLVED:** Yes — three portals discovered (US, Canada EN, Canada FR). See findings above.
- **FR portal dedup**: The Canada FR portal (~45 postings) may overlap with Canada EN (~100 postings) for bilingual regions. Recommend scraping US + Canada EN only initially, then adding Canada FR if Quebec-only postings are missed.
- **WordPress vs iCIMS pagination**: The WordPress frontend shows 604 results but iCIMS US shows ~600 across 40 pages. The slight discrepancy may be due to caching. Scraping iCIMS directly is the recommended approach.
- **Multi-portal company record**: The `companies` table has a single `career_site_url` per company. OSL has 2-3 portals. The iCIMS scraper already supports multi-portal scraping via multiple search URLs — verify this works with the company record design.

## Implementation Effort Estimate

**Low** — no new scraper code required. Need to:
1. Add OSL company record (may need 1-2 records depending on multi-portal support)
2. Configure the 2 English iCIMS portal URLs (`uscareers-oslrs` + `canadaengcareers-oslrs`)
3. Run a test scrape to validate parsing
4. Single commit with a migration adding the company record(s)
