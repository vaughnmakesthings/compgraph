# logo.dev Integration — Design

**Date:** 2026-02-23
**Status:** Approved
**Reference:** `docs/references/logo-dev-api.md`

---

## Goal

Surface company and brand logos throughout CompGraph reports and as map point markers. Use logo.dev's CDN for zero-maintenance logo delivery — no manual uploads, no storage, no rebrand chasing.

---

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Domain storage | Add `domain` column to `brands` + `companies` | logo.dev is domain-keyed; slug heuristics are unreliable for niche brands |
| Brand domain resolution | Option B: backfill existing, enrich-time for new | Clean separation; avoids bloating enrichment runtime for known brands |
| `logo_url` storage | Computed at response time, never stored | Auto-picks up rebrands; simpler DB schema |
| API surface | Two new catalog endpoints (`/api/brands`, `/api/companies`) | Keeps aggregation routes clean; frontend joins locally |
| Aggregation routes | Unchanged | Avoids duplicate join logic across 5+ routes |
| Attribution | Frontend footer ("Logos by Logo.dev") | Free tier requirement; belongs in Shell component, not API |

---

## Schema Changes

### `brands` table — add `domain`

```sql
ALTER TABLE brands ADD COLUMN domain VARCHAR(253);
CREATE INDEX ix_brands_domain ON brands (domain);
```

- Nullable: most existing brands won't have a domain until backfill runs
- Max length 253 = RFC 1035 DNS name limit
- Populated by: backfill script (existing rows), enrichment Pass 2 (new rows)

### `companies` table — add `domain`

```sql
ALTER TABLE companies ADD COLUMN domain VARCHAR(253);
```

- Nullable for safety; manually seeded in migration data
- Known values:
  - T-ROC → `t-roc.com`
  - 2020 Companies → `2020companies.com`
  - BDS → `bdssolutions.com`
  - MarketSource → `marketsource.com`

---

## Config

Two new fields in `src/compgraph/config.py` (pydantic-settings, loaded from `.env`):

```python
LOGO_DEV_PUBLISHABLE_KEY: str = ""   # pk_... — safe for frontend exposure
LOGO_DEV_SECRET_KEY: str = ""        # sk_... — server-side only (Brand Search API)
```

Both stored in 1Password DEV vault.
Frontend: `NEXT_PUBLIC_LOGO_DEV_KEY` in `web/.env.local` (same publishable key value).

---

## Logo URL Helper

New module `src/compgraph/logos.py`:

```python
def logo_url(domain: str | None, size: int = 64, fmt: str = "webp") -> str | None:
    if not domain:
        return None
    return f"https://img.logo.dev/{domain}?token={settings.LOGO_DEV_PUBLISHABLE_KEY}&size={size}&format={fmt}"
```

Pure function — no HTTP call, no DB access. Called at API response serialization time.

---

## API Surface

### `GET /api/brands`

New endpoint. Returns full brand catalog.

**Response schema:**
```json
[
  {
    "id": "uuid",
    "name": "Walmart",
    "slug": "walmart",
    "category": "retail",
    "domain": "walmart.com",
    "logo_url": "https://img.logo.dev/walmart.com?token=pk_...&size=64&format=webp"
  }
]
```

`logo_url` is `null` when `domain` is null (brand not yet resolved).

### `GET /api/companies`

New endpoint. Returns the 4 scraped agencies.

**Response schema:**
```json
[
  {
    "id": "uuid",
    "name": "T-ROC",
    "slug": "t-roc",
    "domain": "t-roc.com",
    "logo_url": "https://img.logo.dev/t-roc.com?token=pk_...&size=64&format=webp"
  }
]
```

### Aggregation routes

Unchanged. The frontend joins brand/company logos from the catalog endpoints using `brand_name` or `company_id` keys already present in aggregation responses.

---

## Backfill Script

`scripts/backfill_brand_domains.py`

1. Query all `brands` WHERE `domain IS NULL`
2. For each brand: `GET https://api.logo.dev/search?q={brand.name}` (secret key, Bearer header)
3. Take `results[0].domain` if results are non-empty
4. Bulk-update `brands.domain` in a single transaction
5. Print summary: N resolved / N skipped (no results) / N failed (API error)

**Run:** `op run --env-file=.env -- uv run python scripts/backfill_brand_domains.py`

---

## Enrichment Integration

During enrichment Pass 2, when a new `Brand` row is first created (entity resolution):

1. Call Brand Search API: `GET https://api.logo.dev/search?q={brand_name}`
2. Set `brand.domain = results[0].domain` if results are non-empty
3. Persist with the brand row creation (same DB transaction)

No change to the enrichment pass structure — domain resolution is a single async HTTP call added to the brand creation path.

---

## Frontend

### Attribution (Free tier requirement)

Add "Logos by [Logo.dev](https://logo.dev)" to the Shell component footer. Small, unobtrusive text link. Required for Free tier compliance.

### Usage pattern

```tsx
// Fetch once, join everywhere
const { data: brands } = useSWR('/api/brands', fetcher);
const logoMap = Object.fromEntries(brands?.map(b => [b.name, b.logo_url]) ?? []);

// In any component
<img src={logoMap['Walmart'] ?? '/fallback-icon.svg'} alt="Walmart logo" width={32} height={32} />
```

### Map markers

```tsx
const icon = L.icon({
  iconUrl: brand.logo_url ?? '/fallback-pin.svg',
  iconSize: [32, 32],
});
```

---

## Implementation Sequence

1. Alembic migration — add `brands.domain` + `companies.domain`, seed company domains
2. Add config keys (`LOGO_DEV_PUBLISHABLE_KEY`, `LOGO_DEV_SECRET_KEY`)
3. Add `src/compgraph/logos.py` helper
4. Add `/api/brands` and `/api/companies` endpoints + tests
5. Run backfill script against dev DB
6. Wire enrichment Pass 2 to resolve domain on new brand creation
7. Frontend: add `NEXT_PUBLIC_LOGO_DEV_KEY` env var, attribution footer, logo usage in components

---

## Out of Scope

- Storing `logo_url` in the database
- Brand Describe API (colors, social links) — defer to future milestone
- Logo caching layer — logo.dev CDN handles this
- Self-hosting logos — Pro tier only, not needed yet
