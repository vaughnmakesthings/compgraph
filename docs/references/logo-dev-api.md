# Logo.dev API — Research Reference

> Researched: 2026-02-23
> Scope: Integration requirements, capabilities, limitations, and implementation patterns for CompGraph

---

## API Overview

Logo.dev provides a REST API for retrieving company logos and brand metadata. The database contains 30M+ company logos, queried primarily by domain.

**Base endpoint:** `https://img.logo.dev/{domain}?token={publishable_key}`

---

## Authentication: Two Key Types

| Key Type | Prefix | Usage | Transport |
|----------|--------|-------|-----------|
| Publishable | `pk_...` | Logo CDN requests (client-safe) | `?token=pk_...` query param |
| Secret | `sk_...` | Brand Search + Brand Describe APIs | `Authorization: Bearer sk_...` header |

**Secret keys are server-side only** — never expose in client code or frontend JavaScript.

CompGraph keys are in 1Password. Use `op run` to inject:
- `LOGO_DEV_PUBLISHABLE_KEY` = `pk_...` (safe in config, can be committed to infra)
- `LOGO_DEV_SECRET_KEY` = `sk_...` (1Password only, never in code)

---

## Endpoints

### 1. Logo Image CDN (Publishable Key)

```
GET https://img.logo.dev/{identifier}?token={pk_key}[&options]
```

**Identifier types:**
- `accenture.com` — domain lookup (most reliable)
- `ACN` — NYSE/NASDAQ ticker
- `US0023111095` — ISIN
- `BTC` — cryptocurrency symbol

**Query parameters:**

| Parameter | Values | Default | Notes |
|-----------|--------|---------|-------|
| `token` | `pk_...` | required | Publishable key |
| `format` | `webp`, `png`, `jpg` | `webp` | `webp` recommended for web |
| `size` | integer (px) | varies | Max 2048px |
| `retina` | `true`, `false` | `false` | 2x resolution for HiDPI |
| `theme` | `light`, `dark` | `light` | Dark mode variant |
| `greyscale` | `true`, `false` | `false` | B&W version |

**Response:** Direct image binary (no JSON wrapper). Returns a fallback monogram if no logo found.

**No API call needed for basic usage** — URLs are deterministic. Generate at build/response time:
```python
def logo_url(domain: str, size: int = 64, fmt: str = "webp") -> str:
    pk = settings.logo_dev_publishable_key
    return f"https://img.logo.dev/{domain}?token={pk}&size={size}&format={fmt}"
```

### 2. Brand Search API (Secret Key)

Search for a company by brand name → returns domain candidates.

```
GET https://api.logo.dev/search?q={brand_name}
Authorization: Bearer sk_...
```

**Use case:** Entity resolution — when we have a brand name but no domain.

**Response:** Array of candidate companies with domains. Useful for fuzzy brand matching against our `brands` table.

### 3. Brand Describe API (Secret Key)

Get logo + metadata for a domain.

```
GET https://api.logo.dev/describe/{domain}
Authorization: Bearer sk_...
```

**Response includes:**
- Logo URL
- Dominant brand colors
- Social media links
- Aspect ratio and transparency info

**Use case:** Enriching our `brands` table with color/social metadata.

---

## Rate Limits & Pricing

| Plan | Monthly Requests | Attribution Required | Batch | Self-host |
|------|-----------------|---------------------|-------|-----------|
| Free | 500,000 | Yes | No | No |
| Pro | Higher | No | Yes | Yes |
| Enterprise | Custom | No | Yes | Yes |

**Enforcement:** Soft limits with proactive notifications (no hard 429 cutoff on Free). Attribution = visible credit on frontend.

**CDN performance:** <50ms global, 200+ edge locations, 99.9%+ uptime.

---

## Key Capabilities

- **Auto-rebrand sync:** When a company rebrands, logos update automatically across all integrations
- **Fallback monograms:** Professional initials-based fallback for missing logos
- **Browser caching:** CDN sets appropriate cache headers
- **Batch export:** Available on Pro/Enterprise (Excel, Google Sheets integration)

---

## Limitations

1. **Domain-first design** — brand name lookup requires the Search API (secret key). Image CDN is domain-based only.
2. **No bulk/batch image endpoint** — batch is Export-oriented (spreadsheets), not a bulk JSON API.
3. **Attribution required on Free** — display a "Logos by Logo.dev" credit if on Free tier.
4. **No webhook** — no push notification for logo changes; CDN handles it transparently.
5. **Rate limit on Search/Describe** — secret key endpoints have stricter limits than the CDN.
6. **No private brands** — only public companies in the database; niche/regional retailers may be missing.

---

## Happy Path

### Frontend (no backend involvement)

For brands/companies where we already have a domain in the DB:

```tsx
// In any React component
const logoUrl = `https://img.logo.dev/${domain}?token=${process.env.NEXT_PUBLIC_LOGO_DEV_KEY}&size=64&format=webp`;

<img src={logoUrl} alt={`${brandName} logo`} width={64} height={64} />
```

### Backend enrichment

For brands missing domain info, use Brand Search during enrichment:

```python
import httpx

async def find_brand_domain(brand_name: str, secret_key: str) -> str | None:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://api.logo.dev/search",
            params={"q": brand_name},
            headers={"Authorization": f"Bearer {secret_key}"},
            timeout=5.0,
        )
        r.raise_for_status()
        results = r.json()
        return results[0]["domain"] if results else None
```

---

## Integration Plan for CompGraph

### Use Case 1: Enrichment Reports (API responses)

**Approach:** Generate logo URLs dynamically in API response serialization. No new DB columns needed for the basic case.

**Files to modify:**
- `src/compgraph/config.py` — add `LOGO_DEV_PUBLISHABLE_KEY` setting
- `src/compgraph/api/routes/` — add `logo_url` field to brand/company response schemas
- `.env` / 1Password — store both keys

**Schema change (optional):** Add `domain` column to `brands` table if missing, since logo.dev is domain-keyed. Also consider `logo_domain` field for brands whose web domain differs from their ATS domain.

**Response example:**
```json
{
  "brand": "Walmart",
  "domain": "walmart.com",
  "logo_url": "https://img.logo.dev/walmart.com?token=pk_...&size=64&format=webp",
  "postings_count": 47
}
```

### Use Case 2: Custom Map Points

**Approach:** Frontend uses logo URLs as custom Leaflet/Mapbox marker icons. Logo URL is deterministic from domain — no backend change needed if frontend has `NEXT_PUBLIC_LOGO_DEV_KEY`.

```tsx
// Leaflet custom icon
const icon = L.icon({
  iconUrl: `https://img.logo.dev/${brand.domain}?token=${LOGO_DEV_KEY}&size=32&format=png`,
  iconSize: [32, 32],
});
```

### Use Case 3: Brand Domain Resolution (Enrichment Pipeline)

When Pass 2 enrichment extracts brand mentions, use Brand Search API to resolve brand name → domain → logo URL. Store `logo_domain` on the `brands` table row.

---

## Recommended Actions

- [ ] Add keys to 1Password DEV vault: `LOGO_DEV_PUBLISHABLE_KEY` and `LOGO_DEV_SECRET_KEY`
- [ ] Add `LOGO_DEV_PUBLISHABLE_KEY` to `src/compgraph/config.py` (pydantic-settings field)
- [ ] Add `NEXT_PUBLIC_LOGO_DEV_KEY` to Next.js env (web frontend)
- [ ] Add `logo_url` field to brand/company API response schemas (computed, not stored)
- [ ] Evaluate whether `brands` table has `domain` column — add if missing
- [ ] Use Brand Search API in enrichment Pass 2 to resolve brand domains
- [ ] Add Brand Describe call to fetch dominant colors (store in `brands.primary_color`)
- [ ] Add attribution link per Free tier requirements if staying on Free plan

---

## Open Questions

1. Does the `brands` table currently have a `domain` column? (Need to check schema)
2. Are we on Free tier (attribution required) or Pro? Attribution affects frontend UX.
3. Should logo URLs be stored in DB or computed at request time? (Computed is simpler, stored enables caching/fallback)
4. Which brands/companies have known domains we can pre-populate? (All 4 scraper companies have known ATS domains)

---

## Sources

- [Logo.dev Documentation](https://www.logo.dev/docs/introduction)
- [API Keys — Logo.dev](https://www.logo.dev/docs/platform/api-keys)
- [Logo API Product Page](https://www.logo.dev/products/logo-api)
- [GitHub: logo-dev/logo-api](https://github.com/logo-dev/logo-api)
