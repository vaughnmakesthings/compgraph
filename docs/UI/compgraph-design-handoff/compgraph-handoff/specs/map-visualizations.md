# Map Visualizations — Component Spec

## Overview

Two map patterns for geographic intelligence: **heatmaps** (job posting density) and **pin maps** (discrete location markers). Both use the same base map styled to match CompGraph's design system.

## Stack

- **Mapbox GL JS** via `react-map-gl` (React wrapper)
- **API key:** Store in `NEXT_PUBLIC_MAPBOX_TOKEN` env var
- **Free tier:** 50k map loads/month (sufficient for B2B internal tool)

```bash
npm install react-map-gl mapbox-gl h3-js
```

- `h3-js` is used server-side for spatial binning (Supabase Edge Functions or API routes). The frontend receives pre-aggregated GeoJSON hexagons.

## Base Map Style

Use Mapbox's `dark-v11` style as the starting point, then override to match CompGraph tokens.

```tsx
import Map from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

<Map
  mapboxAccessToken={process.env.NEXT_PUBLIC_MAPBOX_TOKEN}
  mapStyle="mapbox://styles/mapbox/dark-v11"
  initialViewState={{
    longitude: -95.7,
    latitude: 37.8,
    zoom: 3.5,
  }}
  style={{ width: '100%', height: '100%' }}
/>
```

### Style Overrides

Apply these via Mapbox Studio or runtime style mutations to align with CompGraph:

| Map Element | Default Dark | CompGraph Override |
|---|---|---|
| Land | Mapbox default | `#1A1B26` (dark background) |
| Water | Mapbox default | `#151620` (slightly darker than land) |
| Roads | Mapbox default | `#2D3142` (jet-black) at 40% opacity |
| Labels | Mapbox default | DM Sans where possible, `#9CA3B4` (muted-foreground dark) |
| Borders | Mapbox default | `#4F5D75` (blue-slate) at 30% opacity |
| Parks/green | Mapbox default | `#1B998B` (teal) at 8% opacity |

> **Note:** For light mode, use `light-v11` base and adjust accordingly. Land → `#F4F4F0`, water → `#E8E8E3`, etc. The sidebar remains dark regardless.

---

## Pattern 1: Job Posting Heatmap (H3 Hexagons)

Visualizes density of competitor job postings using **H3 hexagonal spatial indexing**. H3 provides consistent-area hexagonal bins at multiple resolutions, eliminating the misleading density blobs of point-based heatmaps. Hexagons aggregate cleanly, tile without gaps, and transition across zoom levels.

### Dependencies

```bash
npm install h3-js
```

H3 is used for server-side binning (Supabase Edge Functions or API routes). The frontend receives pre-aggregated hex polygons — no H3 computation in the browser.

### H3 Resolution Guide

| Resolution | Avg Hex Area | Avg Edge Length | Use Case |
|---|---|---|---|
| 3 | ~12,393 km² | ~59 km | National overview (zoom 3–5) |
| 4 | ~1,770 km² | ~22 km | Regional view (zoom 5–7) |
| 5 | ~253 km² | ~8.5 km | Metro-level (zoom 7–9) |
| 6 | ~36 km² | ~3.2 km | City-level (zoom 9–11) |
| 7 | ~5.2 km² | ~1.2 km | Neighborhood (zoom 11+) |

**Dynamic resolution:** Map zoom level to H3 resolution for seamless drill-down.

```ts
function zoomToH3Resolution(zoom: number): number {
  if (zoom <= 4) return 3;
  if (zoom <= 6) return 4;
  if (zoom <= 8) return 5;
  if (zoom <= 10) return 6;
  return 7;
}
```

### Server-Side Aggregation

Aggregate postings into H3 cells in Supabase or an API route:

```ts
import { latLngToCell, cellToBoundary } from 'h3-js';

interface HexBin {
  h3Index: string;
  count: number;
  competitors: string[];    // unique competitors in this hex
  topCompetitor?: string;   // highest count
}

function aggregateToHex(
  postings: { latitude: number; longitude: number; competitor: string }[],
  resolution: number
): HexBin[] {
  const bins = new Map<string, { count: number; competitors: Map<string, number> }>();

  for (const p of postings) {
    const h3Index = latLngToCell(p.latitude, p.longitude, resolution);
    const bin = bins.get(h3Index) ?? { count: 0, competitors: new Map() };
    bin.count++;
    bin.competitors.set(p.competitor, (bin.competitors.get(p.competitor) ?? 0) + 1);
    bins.set(h3Index, bin);
  }

  return Array.from(bins.entries()).map(([h3Index, bin]) => {
    const sorted = [...bin.competitors.entries()].sort((a, b) => b[1] - a[1]);
    return {
      h3Index,
      count: bin.count,
      competitors: sorted.map(([name]) => name),
      topCompetitor: sorted[0]?.[0],
    };
  });
}
```

### GeoJSON Conversion

Convert H3 bins to GeoJSON polygons for Mapbox:

```ts
import { cellToBoundary } from 'h3-js';

function hexBinsToGeoJSON(bins: HexBin[]): GeoJSON.FeatureCollection {
  const maxCount = Math.max(...bins.map(b => b.count));

  return {
    type: 'FeatureCollection',
    features: bins.map(bin => {
      // H3 returns [lat, lng] pairs — flip to [lng, lat] for GeoJSON
      const boundary = cellToBoundary(bin.h3Index, true); // true = GeoJSON format [lng, lat]
      // Close the polygon ring
      const ring = [...boundary, boundary[0]];

      return {
        type: 'Feature',
        geometry: {
          type: 'Polygon',
          coordinates: [ring],
        },
        properties: {
          h3Index: bin.h3Index,
          count: bin.count,
          normalized: bin.count / maxCount,  // 0–1 for color interpolation
          competitors: bin.competitors.join(', '),
          topCompetitor: bin.topCompetitor,
        },
      };
    }),
  };
}
```

### Hexagon Fill Layer

```tsx
import { Source, Layer } from 'react-map-gl';

<Source id="hex-bins" type="geojson" data={hexGeoJSON}>
  {/* Filled hexagons — color by density */}
  <Layer
    id="hex-fill"
    type="fill"
    paint={{
      'fill-color': [
        'interpolate', ['linear'], ['get', 'normalized'],
        0,    'rgba(27, 153, 139, 0.15)',   // teal at low density
        0.25, 'rgba(27, 153, 139, 0.5)',    // teal solid
        0.5,  'rgba(239, 131, 84, 0.55)',   // coral at medium
        0.75, 'rgba(220, 178, 86, 0.7)',    // warm-gold at high
        1,    'rgba(255, 255, 255, 0.85)',   // white at peak
      ],
      'fill-opacity': 0.8,
    }}
  />

  {/* Hex outlines — subtle grid */}
  <Layer
    id="hex-outline"
    type="line"
    paint={{
      'line-color': '#4F5D75',     // blue-slate
      'line-width': 0.5,
      'line-opacity': 0.3,
    }}
  />

  {/* Count labels at higher zoom */}
  <Layer
    id="hex-labels"
    type="symbol"
    minzoom={7}
    layout={{
      'text-field': ['get', 'count'],
      'text-font': ['DIN Pro Medium', 'Arial Unicode MS Regular'],
      'text-size': 11,
      'text-allow-overlap': false,
    }}
    paint={{
      'text-color': '#FFFFFF',
      'text-halo-color': '#2D3142',
      'text-halo-width': 1,
    }}
  />
</Source>
```

### Color Ramp (Summary)

| Normalized Value | Color | Token Reference |
|---|---|---|
| 0.00 (lowest) | Teal 15% | `--teal` / `--success` |
| 0.25 (low) | Teal 50% | `--teal` |
| 0.50 (medium) | Coral 55% | `--coral` / `--primary` |
| 0.75 (high) | Gold 70% | `--gold` / `--warning` |
| 1.00 (peak) | White 85% | — |

Cool teal → hot coral/gold → white. Never use red/green.

### Hex Tooltip (on hover)

```tsx
// Use Mapbox interactivity to show hex details on hover
const onHover = useCallback((event: MapLayerMouseEvent) => {
  const feature = event.features?.[0];
  if (!feature) return setHoverInfo(null);

  setHoverInfo({
    longitude: event.lngLat.lng,
    latitude: event.lngLat.lat,
    count: feature.properties.count,
    topCompetitor: feature.properties.topCompetitor,
  });
}, []);

<Map interactiveLayerIds={['hex-fill']} onMouseMove={onHover}>
  {/* ... layers ... */}

  {hoverInfo && (
    <Popup
      longitude={hoverInfo.longitude}
      latitude={hoverInfo.latitude}
      closeButton={false}
      anchor="bottom"
      offset={8}
      className="compgraph-map-popup"
    >
      <div className="font-mono text-lg font-medium text-foreground">
        {hoverInfo.count}
      </div>
      <div className="font-body text-xs text-muted-foreground">
        postings in this area
      </div>
      {hoverInfo.topCompetitor && (
        <div className="font-body text-xs text-muted-foreground mt-1">
          Top: <span className="text-foreground font-medium">{hoverInfo.topCompetitor}</span>
        </div>
      )}
    </Popup>
  )}
</Map>
```

### Dynamic Resolution on Zoom

Re-fetch hex bins when the user zooms to a new resolution threshold:

```tsx
const [h3Resolution, setH3Resolution] = useState(3);

const onZoomEnd = useCallback((event: ViewStateChangeEvent) => {
  const newRes = zoomToH3Resolution(event.viewState.zoom);
  if (newRes !== h3Resolution) {
    setH3Resolution(newRes);
    // Trigger data re-fetch at new resolution
    fetchHexBins(newRes);
  }
}, [h3Resolution]);

<Map onZoomEnd={onZoomEnd}>
```

### Point Layer (High Zoom Fallback)

At zoom 12+, hex bins become too small to be useful. Transition to individual posting dots:

```tsx
<Layer
  id="postings-points"
  type="circle"
  minzoom={11}
  paint={{
    'circle-radius': [
      'interpolate', ['linear'], ['zoom'],
      11, 3,
      14, 6,
    ],
    'circle-color': '#EF8354',          // coral
    'circle-opacity': [
      'interpolate', ['linear'], ['zoom'],
      11, 0,
      12, 0.8,
    ],
    'circle-stroke-width': 1,
    'circle-stroke-color': '#2D3142',   // jet-black outline
  }}
/>
```

### Supabase Storage Strategy

Pre-compute H3 indices at ingest time for fast aggregation:

```sql
-- Add H3 index columns to job_postings table
ALTER TABLE job_postings
  ADD COLUMN h3_res3 TEXT,
  ADD COLUMN h3_res4 TEXT,
  ADD COLUMN h3_res5 TEXT,
  ADD COLUMN h3_res6 TEXT,
  ADD COLUMN h3_res7 TEXT;

-- Index for fast GROUP BY aggregation
CREATE INDEX idx_postings_h3_res3 ON job_postings (h3_res3);
CREATE INDEX idx_postings_h3_res4 ON job_postings (h3_res4);
CREATE INDEX idx_postings_h3_res5 ON job_postings (h3_res5);
CREATE INDEX idx_postings_h3_res6 ON job_postings (h3_res6);
CREATE INDEX idx_postings_h3_res7 ON job_postings (h3_res7);

-- Aggregation query (example for resolution 4)
SELECT
  h3_res4 AS h3_index,
  COUNT(*) AS count,
  ARRAY_AGG(DISTINCT competitor_name) AS competitors,
  MODE() WITHIN GROUP (ORDER BY competitor_name) AS top_competitor
FROM job_postings
WHERE h3_res4 IS NOT NULL
GROUP BY h3_res4;
```

Populate H3 indices on insert via a Supabase Edge Function or trigger using the `h3-js` library.

---

## Pattern 2: Pin Map (Location Markers)

Discrete markers for specific locations (offices, retail stores, competitor HQs, etc.).

### Data Shape

```ts
interface MapPin {
  id: string;
  latitude: number;
  longitude: number;
  label: string;
  category?: string;     // for color coding (uses chart palette)
  value?: number;        // optional numeric badge
  active?: boolean;      // highlight state
}
```

### Implementation

Use `react-map-gl` Marker components for <100 pins. For larger datasets, use a symbol layer.

#### Small Dataset (<100 pins) — React Markers

```tsx
import { Marker, Popup } from 'react-map-gl';

const CATEGORY_COLORS: Record<string, string> = {
  'Tier 1': '#EF8354',   // coral (chart-1)
  'Tier 2': '#1B998B',   // teal (chart-2)
  'Tier 3': '#4F5D75',   // blue-slate (chart-3)
};

{pins.map(pin => (
  <Marker key={pin.id} longitude={pin.longitude} latitude={pin.latitude}>
    <button
      className="group relative flex items-center justify-center"
      onClick={() => setSelectedPin(pin)}
      aria-label={pin.label}
    >
      {/* Pin dot */}
      <span
        className="w-3 h-3 rounded-full border-2 border-[#2D3142] transition-transform duration-100 group-hover:scale-125"
        style={{
          backgroundColor: CATEGORY_COLORS[pin.category] ?? '#EF8354',
          boxShadow: pin.active ? '0 0 6px currentColor' : 'none',
        }}
      />

      {/* Optional count badge */}
      {pin.value != null && (
        <span className="absolute -top-5 left-1/2 -translate-x-1/2 font-mono text-[11px] text-white bg-[#2D3142] px-1.5 py-0.5 rounded-sm whitespace-nowrap">
          {pin.value}
        </span>
      )}
    </button>
  </Marker>
))}
```

#### Large Dataset (100+ pins) — Symbol Layer

```tsx
<Source id="locations" type="geojson" data={geojson}>
  <Layer
    id="location-pins"
    type="circle"
    paint={{
      'circle-radius': 5,
      'circle-color': [
        'match', ['get', 'category'],
        'Tier 1', '#EF8354',
        'Tier 2', '#1B998B',
        'Tier 3', '#4F5D75',
        '#BFC0C0',  // fallback: silver
      ],
      'circle-stroke-width': 1.5,
      'circle-stroke-color': '#2D3142',
      'circle-opacity': 0.85,
    }}
  />
</Source>
```

### Popup / Tooltip

```tsx
{selectedPin && (
  <Popup
    longitude={selectedPin.longitude}
    latitude={selectedPin.latitude}
    onClose={() => setSelectedPin(null)}
    closeButton={false}
    anchor="bottom"
    offset={12}
    className="compgraph-map-popup"
  >
    <div className="font-body text-sm text-foreground font-medium">
      {selectedPin.label}
    </div>
    {selectedPin.value != null && (
      <div className="font-mono text-xs text-muted-foreground mt-0.5">
        {selectedPin.value} postings
      </div>
    )}
  </Popup>
)}
```

**Popup styles** (add to global CSS):

```css
.compgraph-map-popup .mapboxgl-popup-content {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 14px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  font-family: var(--font-body);
}

.dark .compgraph-map-popup .mapboxgl-popup-content {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.compgraph-map-popup .mapboxgl-popup-tip {
  border-top-color: var(--surface);
}
```

---

## Map Container

Both patterns share the same container component:

```tsx
interface MapContainerProps {
  children: React.ReactNode;
  height?: string;          // default '400px', use '100%' for full-page
  initialView?: {
    longitude: number;
    latitude: number;
    zoom: number;
  };
}

export function MapContainer({
  children,
  height = '400px',
  initialView = { longitude: -95.7, latitude: 37.8, zoom: 3.5 },
}: MapContainerProps) {
  return (
    <div
      className="rounded-lg border border-border overflow-hidden"
      style={{ height }}
    >
      <Map
        mapboxAccessToken={process.env.NEXT_PUBLIC_MAPBOX_TOKEN}
        mapStyle="mapbox://styles/mapbox/dark-v11"
        initialViewState={initialView}
        style={{ width: '100%', height: '100%' }}
        attributionControl={false}
      >
        <NavigationControl position="top-right" showCompass={false} />
        {children}
      </Map>
    </div>
  );
}
```

| Property | Value |
|---|---|
| Border | 1px `var(--border)` |
| Radius | `var(--radius-lg)` (8px) |
| Overflow | hidden (clips map to rounded corners) |
| Default height | 400px (card embed), 100% (full page) |
| Default center | US center (-95.7, 37.8) at zoom 3.5 |
| Nav control | Top-right, no compass, zoom +/- only |
| Attribution | Hidden (add manual credit in footer if needed) |

---

## Map Legend

Shared legend component for both patterns:

```tsx
export function MapLegend({ items }: { items: { color: string; label: string }[] }) {
  return (
    <div className="absolute bottom-4 left-4 bg-surface/90 backdrop-blur-sm border border-border rounded-md px-3 py-2 flex flex-col gap-1.5">
      {items.map(item => (
        <div key={item.label} className="flex items-center gap-2">
          <span
            className="w-2.5 h-2.5 rounded-full flex-shrink-0"
            style={{ backgroundColor: item.color }}
          />
          <span className="font-body text-xs text-muted-foreground">
            {item.label}
          </span>
        </div>
      ))}
    </div>
  );
}
```

**Heatmap legend** uses a gradient bar to represent hex fill density:

```tsx
export function HeatmapLegend() {
  return (
    <div className="absolute bottom-4 left-4 bg-surface/90 backdrop-blur-sm border border-border rounded-md px-3 py-2.5">
      <div className="font-body text-xs text-muted-foreground mb-1.5">Posting Density (H3 Hex)</div>
      <div
        className="w-32 h-2 rounded-full"
        style={{
          background: 'linear-gradient(to right, #1B998B, #EF8354, #DCB256, #FFFFFF)',
        }}
      />
      <div className="flex justify-between mt-1">
        <span className="font-mono text-[10px] text-muted-foreground">Low</span>
        <span className="font-mono text-[10px] text-muted-foreground">High</span>
      </div>
    </div>
  );
}
```

---

## Usage Examples

### Dashboard: National H3 Heatmap Card

```tsx
<Card>
  <CardHeader>
    <MapPinIcon className="w-4 h-4 text-muted-foreground" />
    <CardTitle>Posting Activity by Region</CardTitle>
  </CardHeader>
  <CardContent className="p-0">
    <MapContainer height="320px">
      <HexHeatmapLayer resolution={h3Resolution} data={hexBins} />
      <HeatmapLegend />
    </MapContainer>
  </CardContent>
</Card>
```

### Competitor Detail: Office Locations

```tsx
<Card>
  <CardHeader>
    <BuildingOfficeIcon className="w-4 h-4 text-muted-foreground" />
    <CardTitle>Known Locations</CardTitle>
  </CardHeader>
  <CardContent className="p-0">
    <MapContainer height="300px">
      <PinLayer pins={competitorLocations} />
      <MapLegend items={[
        { color: '#EF8354', label: 'HQ' },
        { color: '#1B998B', label: 'Regional Office' },
        { color: '#4F5D75', label: 'Field Market' },
      ]} />
    </MapContainer>
  </CardContent>
</Card>
```

---

## Anti-Patterns

- ❌ Do not use Mapbox's built-in `heatmap` layer type — use H3 hex polygons for accurate spatial binning
- ❌ Do not compute H3 indices in the browser — pre-compute server-side and send GeoJSON
- ❌ Do not use Mapbox default popups without restyling — always apply CompGraph popup CSS
- ❌ Do not use red/green for density — use the teal → coral → gold ramp
- ❌ Do not show attribution bar (it covers the rounded corners) — add credit in page footer
- ❌ Do not use 3D terrain or globe projection — keep it flat and functional
- ❌ Do not use map for <5 data points — use a simple list instead
- ❌ Do not animate pin drops — keep it static and scannable
