# HTTP 308 Redirect Handling

> Reference for CompGraph API versioning. Covers how browsers, httpx, and requests handle
> 308 Permanent Redirect for non-GET methods with payloads and Authorization headers.
> Use case: adding `/api/v1/` prefix with 308 redirect from `/api/` for backward compat.

---

## Quick Reference

| Behavior | 301 | 302 | 307 | 308 |
|----------|-----|-----|-----|-----|
| Permanent? | Yes | No | No | **Yes** |
| Preserves method (POST/PUT/DELETE)? | No (may become GET) | No (may become GET) | **Yes** | **Yes** |
| Preserves request body? | No | No | **Yes** | **Yes** |
| Cacheable by default? | Yes | No | No | **Yes** |

**TL;DR:** 308 = permanent + method-preserving + body-preserving. Use 308 (not 301) when redirecting POST/PUT/DELETE endpoints.

---

## S1 Browser Fetch API Behavior

### Method and Body Preservation

Per the [Fetch Standard](https://fetch.spec.whatwg.org/), 307/308 redirects **must** reuse the original method and body. All major browsers comply.

```javascript
// This POST to /api/postings will follow 308 to /api/v1/postings
// preserving POST method and JSON body
const res = await fetch("/api/postings", {
  method: "POST",
  headers: { "Content-Type": "application/json", Authorization: "Bearer xxx" },
  body: JSON.stringify({ title: "test" }),
});
// res.url === "/api/v1/postings" (redirected)
// res.redirected === true
```

### Authorization Header Stripping

| Redirect type | Auth header preserved? |
|---------------|----------------------|
| Same-origin (e.g., `/api/` → `/api/v1/`) | **Yes** — all browsers |
| Cross-origin (e.g., `site-a.com` → `site-b.com`) | **No** — stripped per spec |

This is standardized in [whatwg/fetch#944](https://github.com/whatwg/fetch/issues/944). Chrome, Firefox, and Safari all strip `Authorization` on cross-origin redirects.

**CompGraph implication:** The Vercel rewrite (`/api/*` → `dev.compgraph.io/api/*`) is a proxy, not a redirect — the browser never sees a cross-origin hop. If the FastAPI backend itself issues a 308 redirect (e.g., `/api/postings` → `/api/v1/postings`), it is same-origin from the browser's perspective (both `dev.compgraph.io`), so auth headers are preserved.

### Browser-Specific Quirks

| Browser | Quirk |
|---------|-------|
| **Chrome** | Fully spec-compliant since ~Chrome 111. Strips auth on cross-origin. |
| **Safari** | Historically stripped auth even on same-origin redirects. Fixed in Safari 16.3+. Older Safari versions may lose auth on any redirect. |
| **Firefox** | `network.fetch.redirect.stripAuthHeader` pref controls behavior. Bug [1817980](https://bugzilla.mozilla.org/show_bug.cgi?id=1817980) caused same-origin stripping in some builds. |

---

## S2 Python HTTP Client Behavior

### httpx

```python
import httpx

# httpx does NOT follow redirects by default
response = httpx.post(
    "https://dev.compgraph.io/api/postings",
    json={"title": "test"},
    headers={"Authorization": "Bearer xxx"},
    follow_redirects=True,  # Must opt in
)
```

| Behavior | httpx |
|----------|-------|
| Default `follow_redirects` | `False` |
| 308 preserves method? | Yes |
| 308 preserves body? | Yes |
| Auth on same-origin redirect? | Preserved |
| Auth on cross-origin redirect? | **Stripped** ([encode/httpx#3291](https://github.com/encode/httpx/discussions/3291)) |

### requests

```python
import requests

# requests follows redirects by default
response = requests.post(
    "https://dev.compgraph.io/api/postings",
    json={"title": "test"},
    headers={"Authorization": "Bearer xxx"},
    # allow_redirects=True is the default
)
```

| Behavior | requests |
|----------|----------|
| Default `allow_redirects` | `True` |
| 308 preserves method? | Yes |
| 308 preserves body? | Yes (file-like bodies rewound via `seek(0)`) |
| Auth on cross-origin redirect? | **Stripped** |

**Historical bug (fixed):** [psf/requests#1084](https://github.com/psf/requests/issues/1084) — early versions dropped body on 307 redirects. Fixed in requests 2.x.

---

## S3 CORS Preflight Interaction

**Browsers reject redirects on OPTIONS preflight requests.** This is the single biggest 308 gotcha.

```
Browser → OPTIONS /api/postings (preflight)
Server → 308 /api/v1/postings
Browser → ❌ "Redirect is not allowed for a preflight request"
```

The preflight must respond with `200` or `204` directly. A redirect response (any 3xx) causes the entire CORS request to fail per the [Fetch Standard](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS/Errors/CORSExternalRedirectNotAllowed).

**CompGraph impact:** If the FastAPI backend adds 308 redirects from `/api/` to `/api/v1/`, the Vercel rewrite handles the proxy transparently — CORS headers come from Caddy on the DO server, not from the redirect. But if a browser ever hits the backend directly (e.g., dev mode against `localhost:8000`), preflighted requests (POST/PUT/DELETE with `Authorization` header) **will fail** if they hit a 308.

### Mitigation

```python
# In FastAPI: respond to OPTIONS directly, only redirect other methods
from fastapi import Request
from fastapi.responses import RedirectResponse

@app.middleware("http")
async def redirect_legacy_api(request: Request, call_next):
    if request.url.path.startswith("/api/") and not request.url.path.startswith("/api/v1/"):
        if request.method == "OPTIONS":
            # Let the CORS middleware handle OPTIONS directly
            return await call_next(request)
        new_path = request.url.path.replace("/api/", "/api/v1/", 1)
        return RedirectResponse(url=new_path, status_code=308)
    return await call_next(request)
```

---

## S4 Vercel Rewrite vs Redirect

Vercel `vercel.json` rewrites are **server-side proxies**, not HTTP redirects. The browser sees the original URL.

```json
{
  "rewrites": [
    { "source": "/api/:path*", "destination": "https://dev.compgraph.io/api/:path*" }
  ]
}
```

- No 308 is sent to the browser — Vercel's edge fetches from the destination and returns the response.
- CORS is not triggered (same-origin from browser's perspective).
- If the backend itself returns a 308, Vercel's proxy follows it server-side before returning to the browser.

**Vercel redirects** (different from rewrites) do send 3xx to the browser:

```json
{
  "redirects": [
    { "source": "/old-api/:path*", "destination": "/api/v1/:path*", "permanent": true }
  ]
}
```

`"permanent": true` sends 308 (not 301) for non-GET methods in Vercel.

---

## S5 Recommended Pattern for CompGraph

**Goal:** Add `/api/v1/` prefix, keep `/api/` working for backward compat.

### Option A: Vercel rewrite (preferred for frontend)

```json
{
  "rewrites": [
    { "source": "/api/:path*", "destination": "https://dev.compgraph.io/api/v1/:path*" }
  ]
}
```

No redirect involved. Frontend keeps calling `/api/*`, Vercel proxies to `/api/v1/*` on the backend. Zero client changes.

### Option B: FastAPI redirect (for direct API consumers)

```python
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

legacy = APIRouter()

@legacy.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def legacy_redirect(path: str):
    return RedirectResponse(
        url=f"/api/v1/{path}",
        status_code=308,  # Preserves method + body
    )
```

Add explicit OPTIONS handling if CORS is needed on the legacy paths.

### Option C: Mount both (simplest)

```python
# Mount the same router at both prefixes
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api")  # Legacy, no redirect needed
```

No redirects at all. Both paths serve the same handlers. Deprecate `/api/` later.

---

## Gotchas & Limitations

| Issue | Impact | Mitigation |
|-------|--------|------------|
| CORS preflight + 308 = failure | POST/PUT/DELETE from browsers fail | Handle OPTIONS separately (S3) |
| Safari <16.3 strips auth on same-origin 308 | Auth lost after redirect | Use rewrite instead of redirect |
| httpx default `follow_redirects=False` | Client gets 308 response, not final resource | Set `follow_redirects=True` explicitly |
| `requests` file upload body on 307/308 | Body must be seekable for rewind | Use `bytes` not generators for upload bodies |
| 308 is cached by browsers permanently | Can't "undo" a 308 without cache clear | Test thoroughly; use 307 during development |
| Vercel rewrites have 120s proxy timeout | Long backend responses timeout | See `vercel-do-timeout-patterns.md` |

---

## Sources

- [MDN: 308 Permanent Redirect](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/308)
- [Fetch Standard (whatwg)](https://fetch.spec.whatwg.org/)
- [whatwg/fetch#944 — Drop Authorization header on cross-origin redirects](https://github.com/whatwg/fetch/issues/944)
- [whatwg/fetch#1662 — Request body reuse in 307/308 redirects](https://github.com/whatwg/fetch/issues/1662)
- [Chromium: Remove Authorization header upon cross-origin redirect](https://groups.google.com/a/chromium.org/g/blink-dev/c/3Zt4UHbynYA/m/9CZ3fFdnAQAJ)
- [Mozilla Bug 1817980 — Same-origin auth header stripping](https://bugzilla.mozilla.org/show_bug.cgi?id=1817980)
- [HTTPX: follow_redirects dropping Bearer token](https://github.com/encode/httpx/discussions/3291)
- [HTTPX: Compatibility with requests](https://www.python-httpx.org/compatibility/)
- [psf/requests#1084 — POST body lost on 307 redirect](https://github.com/psf/requests/issues/1084)
- [MDN: CORS external redirect not allowed](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS/Errors/CORSExternalRedirectNotAllowed)
- [Vercel: Rewrites documentation](https://vercel.com/docs/rewrites)
- [Vercel: CDN origin timeout increased to 2 minutes](https://vercel.com/changelog/cdn-origin-timeout-increased-to-two-minutes)
- [Baeldung: Redirection Status Codes 301, 302, 307, 308](https://www.baeldung.com/cs/redirection-status-codes)
