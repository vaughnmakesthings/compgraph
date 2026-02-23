# Logo.dev Integration — Component Spec

## Overview

Logo.dev provides instant company logos via CDN for any domain. CompGraph uses it to visually enrich competitor profiles, client lists, data tables, and map markers with professional brand logos — no manual image management.

## APIs

Logo.dev has two APIs with different auth models:

| API | Base URL | Auth | Use |
|---|---|---|---|
| **Image CDN** | `https://img.logo.dev/` | Publishable key (`token` param) | Client-side `<img>` tags |
| **Brand Search** | `https://api.logo.dev/search` | Secret key (`Authorization` header) | Server-side domain resolution |

### Environment Variables

```env
# Client-safe — used in <img> src URLs
NEXT_PUBLIC_LOGO_DEV_TOKEN=pk_...

# Server-only — used in API routes / Edge Functions
LOGO_DEV_SECRET_KEY=sk_...
```

**Never expose the secret key to the browser.** Publishable keys are safe in client code — Logo.dev rate-limits and blocks abuse automatically.

---

## Image CDN API

Returns a logo image for any domain. Use directly in `<img>` tags.

### Endpoint

```
https://img.logo.dev/{domain}?token={NEXT_PUBLIC_LOGO_DEV_TOKEN}
```

### Parameters

| Param | Type | Default | Notes |
|---|---|---|---|
| `token` | string | required | Publishable key |
| `size` | integer | 128 | Max 800px. Recommendation: ≤256 for raster |
| `format` | string | `jpg` | `jpg`, `png`, `webp`. Use `png` for transparency. |
| `theme` | string | `auto` | `dark` for dark backgrounds, `light` for light. Requires PNG transparency. |
| `greyscale` | boolean | `false` | Desaturated logos — useful for normalizing visual weight |
| `retina` | boolean | `false` | Doubles source resolution for HiDPI. Set CSS `width`/`height` to display size. |
| `fallback` | string | `monogram` | `monogram` = auto-generated letter mark. `404` = HTTP 404 if unknown. |

### Lookup Modes

```
# By domain (most reliable)
https://img.logo.dev/google.com?token=pk_...

# By company name (fuzzy match, returns first Brand Search result)
https://img.logo.dev/name/BDS%20Connected%20Solutions?token=pk_...

# By stock ticker
https://img.logo.dev/ticker/GOOG?token=pk_...
```

**Use domain lookup whenever possible.** Name lookup is a convenience for when you only have a brand name.

---

## Brand Search API

Server-side only. Resolves brand names to domains for logo lookup.

### Endpoint

```
GET https://api.logo.dev/search?q={query}&strategy={typeahead|match}
```

### Auth

```ts
const response = await fetch(`https://api.logo.dev/search?q=${encodeURIComponent(query)}`, {
  headers: {
    Authorization: `Bearer ${process.env.LOGO_DEV_SECRET_KEY}`,
  },
});
```

### Response

```json
[
  { "name": "BDS Connected Solutions", "domain": "bfrb.com" },
  { "name": "BDS Marketing", "domain": "bdsmarketing.com" }
]
```

Max 10 results, sorted by popularity. Use `strategy=match` for exact matching, `strategy=typeahead` (default) for autocomplete.

---

## Integration Points

### 1. Competitor Logos in Data Tables

The most frequent use. Show logos inline next to competitor names.

```tsx
function CompetitorLogo({
  domain,
  name,
  size = 24,
}: {
  domain?: string;
  name: string;
  size?: number;
}) {
  const token = process.env.NEXT_PUBLIC_LOGO_DEV_TOKEN;
  const src = domain
    ? `https://img.logo.dev/${domain}?token=${token}&size=${size * 2}&format=png&fallback=monogram&retina=true`
    : `https://img.logo.dev/name/${encodeURIComponent(name)}?token=${token}&size=${size * 2}&format=png&fallback=monogram&retina=true`;

  return (
    <img
      src={src}
      alt={`${name} logo`}
      width={size}
      height={size}
      className="rounded-sm flex-shrink-0"
      loading="lazy"
      onError={(e) => {
        // Hide broken images gracefully
        (e.target as HTMLImageElement).style.display = 'none';
      }}
    />
  );
}
```

**Table row usage:**

```tsx
<tr>
  <td className="flex items-center gap-3 py-3 px-4">
    <CompetitorLogo domain="marketsource.com" name="MarketSource" />
    <span className="font-body text-sm text-foreground">MarketSource</span>
  </td>
  <td className="font-mono text-[13px]">312</td>
  {/* ... */}
</tr>
```

### 2. Competitor Profile Cards

Larger logo treatment for detail pages and profile headers.

```tsx
<div className="flex items-center gap-4">
  <div className="w-12 h-12 rounded-lg border border-border overflow-hidden bg-muted flex items-center justify-center">
    <CompetitorLogo domain={competitor.domain} name={competitor.name} size={48} />
  </div>
  <div>
    <h2 className="font-display text-xl font-semibold">{competitor.name}</h2>
    <span className="font-body text-sm text-muted-foreground">{competitor.domain}</span>
  </div>
</div>
```

### 3. Sidebar Leaf Items (Optional Enhancement)

Replace the colored dots with tiny logos for competitors that have resolved domains.

```tsx
<Link href={`/competitors/${competitor.slug}`} className="sidebar-leaf">
  {competitor.domain ? (
    <img
      src={`https://img.logo.dev/${competitor.domain}?token=${token}&size=28&format=png&fallback=monogram&retina=true`}
      alt=""
      width={14}
      height={14}
      className="rounded-[2px] flex-shrink-0"
      loading="lazy"
    />
  ) : (
    <span className="sidebar-leaf-dot" style={{ backgroundColor: chartColor }} />
  )}
  <span>{competitor.name}</span>
  <span className="sidebar-leaf-count">{competitor.postingCount}</span>
</Link>
```

> **Design note:** This is an opt-in enhancement. The colored dot is the default. Only swap to logos when domains have been resolved and verified. Mixed dot/logo states look inconsistent — go all-or-nothing per tier group.

### 4. Map Pin Markers (Custom Logo Pins)

Use logos as custom Mapbox markers instead of plain circles. Best for pin maps with <50 markers where individual identity matters.

```tsx
import { Marker } from 'react-map-gl';

function LogoMapMarker({
  pin,
  isActive,
  onClick,
}: {
  pin: MapPin & { domain?: string };
  isActive: boolean;
  onClick: () => void;
}) {
  const token = process.env.NEXT_PUBLIC_LOGO_DEV_TOKEN;

  return (
    <Marker longitude={pin.longitude} latitude={pin.latitude}>
      <button
        onClick={onClick}
        className={cn(
          'relative flex items-center justify-center',
          'w-8 h-8 rounded-full border-2 bg-surface shadow-md',
          'transition-transform duration-100 hover:scale-110',
          isActive
            ? 'border-primary scale-110 shadow-lg'
            : 'border-border',
        )}
        aria-label={pin.label}
      >
        {pin.domain ? (
          <img
            src={`https://img.logo.dev/${pin.domain}?token=${token}&size=48&format=png&fallback=monogram&retina=true`}
            alt=""
            width={20}
            height={20}
            className="rounded-full"
          />
        ) : (
          <span className="font-display text-[10px] font-bold text-muted-foreground">
            {pin.label.charAt(0)}
          </span>
        )}
      </button>

      {/* Pin tail */}
      <div className={cn(
        'w-0 h-0 mx-auto -mt-[2px]',
        'border-l-[6px] border-l-transparent',
        'border-r-[6px] border-r-transparent',
        'border-t-[6px]',
        isActive ? 'border-t-primary' : 'border-t-border',
      )} />
    </Marker>
  );
}
```

**When to use logo markers vs. plain circles:**

| Scenario | Marker Type |
|---|---|
| <30 pins, each a known company | Logo markers |
| 30–100 pins, mixed known/unknown | Plain circle markers (chart palette) |
| 100+ pins | Mapbox circle layer (no React markers) |
| H3 heatmap overlay active | Never — hexes only |

### 5. Domain Resolution at Ingest

When scraping job postings, resolve competitor domains server-side and store them for logo lookup.

```ts
// API route: /api/resolve-domain
import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const name = searchParams.get('name');

  if (!name) return NextResponse.json({ error: 'name required' }, { status: 400 });

  const res = await fetch(
    `https://api.logo.dev/search?q=${encodeURIComponent(name)}&strategy=match`,
    {
      headers: {
        Authorization: `Bearer ${process.env.LOGO_DEV_SECRET_KEY}`,
      },
    }
  );

  if (!res.ok) return NextResponse.json({ error: 'search failed' }, { status: 502 });

  const results = await res.json();
  const topMatch = results[0] ?? null;

  return NextResponse.json({
    query: name,
    domain: topMatch?.domain ?? null,
    matchedName: topMatch?.name ?? null,
  });
}
```

**Database schema addition:**

```sql
ALTER TABLE competitors
  ADD COLUMN domain TEXT,
  ADD COLUMN domain_resolved_at TIMESTAMPTZ,
  ADD COLUMN logo_url TEXT GENERATED ALWAYS AS (
    CASE WHEN domain IS NOT NULL
      THEN 'https://img.logo.dev/' || domain || '?token=' || current_setting('app.logo_dev_token', true) || '&size=128&format=png'
      ELSE NULL
    END
  ) STORED;
```

> **Alternative:** Don't store generated URLs. Just store the `domain` column and build URLs at render time. The generated column approach above is only useful if you're querying logo URLs from SQL directly (e.g., in exports).

---

## Recommended Defaults

Standard parameters to use across the app for consistency:

```ts
// lib/logo.ts
const LOGO_DEV_TOKEN = process.env.NEXT_PUBLIC_LOGO_DEV_TOKEN;

export function logoUrl(
  domain: string,
  opts: {
    size?: number;
    format?: 'png' | 'jpg' | 'webp';
    greyscale?: boolean;
    theme?: 'light' | 'dark' | 'auto';
    retina?: boolean;
    fallback?: 'monogram' | '404';
  } = {}
): string {
  const {
    size = 128,
    format = 'png',
    greyscale = false,
    theme = 'auto',
    retina = true,
    fallback = 'monogram',
  } = opts;

  const params = new URLSearchParams({
    token: LOGO_DEV_TOKEN!,
    size: String(size),
    format,
    theme,
    fallback,
  });
  if (greyscale) params.set('greyscale', 'true');
  if (retina) params.set('retina', 'true');

  return `https://img.logo.dev/${domain}?${params}`;
}

export function logoUrlByName(name: string, opts = {}): string {
  return logoUrl(`name/${encodeURIComponent(name)}`, opts);
}
```

**Standard presets:**

| Context | Size | Format | Theme | Retina |
|---|---|---|---|---|
| Table row (24px display) | 48 | png | auto | true |
| Card avatar (48px display) | 96 | png | auto | true |
| Sidebar (14px display) | 28 | png | dark | true |
| Map marker (20px display) | 40 | png | auto | true |
| Profile hero (64px display) | 128 | png | auto | true |
| Greyscale grid (client wall) | 128 | png | auto | true + greyscale |

---

## Greyscale Grid (Client Walls)

For "Clients Served" or "Retailers Covered" sections, use greyscale logos in a grid:

```tsx
<div className="grid grid-cols-4 gap-6 items-center justify-items-center py-8">
  {retailers.map(r => (
    <img
      key={r.domain}
      src={logoUrl(r.domain, { size: 128, greyscale: true })}
      alt={r.name}
      width={64}
      height={64}
      className="opacity-50 hover:opacity-100 transition-opacity duration-150"
    />
  ))}
</div>
```

This matches the SaaS "trusted by" pattern but applied to CompGraph's competitor-client intelligence.

---

## Caching Strategy

Logo.dev CDN handles caching automatically via HTTP cache headers. For additional performance:

1. **Next.js Image Optimization** — Use `<Image>` component with `unoptimized` prop (Logo.dev already optimizes):
   ```tsx
   import Image from 'next/image';
   <Image src={logoUrl(domain)} width={24} height={24} alt="" unoptimized />
   ```

2. **Supabase Storage mirror** (optional, for offline/export use) — Download logos to Supabase Storage bucket on competitor creation. Serve from your own CDN for PDF exports or offline views.

---

## Attribution

Free tier requires a visible attribution link to Logo.dev wherever logos are displayed. Add to the page footer:

```tsx
<footer className="text-xs text-muted-foreground">
  Logos provided by <a href="https://logo.dev" className="underline">Logo.dev</a>
</footer>
```

Paid plans ($300/yr+) remove the attribution requirement.

---

## Anti-Patterns

- ❌ Do not hardcode the publishable key in source — use `NEXT_PUBLIC_LOGO_DEV_TOKEN` env var
- ❌ Do not expose the secret key (`sk_`) to the browser — server-side only
- ❌ Do not download and self-host logos on the free plan — this requires Pro/Enterprise
- ❌ Do not use JPG format for sidebar/dark backgrounds — use PNG for transparency support
- ❌ Do not show mixed dot/logo states in the sidebar — go all-or-nothing per tier group
- ❌ Do not use logo markers for H3 heatmaps — logos are for pin maps only
- ❌ Do not skip the `fallback` param — always specify `monogram` or `404` to handle unknowns gracefully
- ❌ Do not request sizes above 256px for raster formats — diminishing quality returns
