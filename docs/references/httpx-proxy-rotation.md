# httpx Proxy Rotation & Session Stickiness

> Reference for adding proxy support to CompGraph scrapers (iCIMS x2, Workday CXS x2).

## Quick Reference

| Concept | CompGraph Pattern |
|---|---|
| Sticky session | One proxy IP per company scrape run (not per request) |
| Rotation point | Between runs — new company = may get new IP |
| Current state | `proxy.py` exists with `get_proxy_client_kwargs()` + UA rotation |
| Config | `PROXY_URL`, `PROXY_USERNAME`, `PROXY_PASSWORD` in Settings |
| Client | `httpx.AsyncClient(proxy=url)` — proxy locked at client init |

## httpx Proxy Configuration

### Client-Level (Sticky — Use This)

```python
# Proxy is fixed for all requests made by this client instance
async with httpx.AsyncClient(proxy="http://user:pass@proxy:8080") as client:
    await client.get("https://careers.example.com/page/1")  # same IP
    await client.get("https://careers.example.com/page/2")  # same IP
```

### Per-Request (Rotating — Avoid for CompGraph)

```python
# Top-level functions accept proxy= but create a new connection each time
resp = httpx.get("https://example.com", proxy="http://proxy:8080")
```

### Connection Pool Limits

```python
limits = httpx.Limits(
    max_connections=100,       # total concurrent (default)
    max_keepalive_connections=20,  # idle pool size (default)
    keepalive_expiry=5.0,      # seconds
)
client = httpx.AsyncClient(proxy=proxy_url, limits=limits)
```

For scraping, lower these — `max_connections=10, max_keepalive_connections=5` prevents aggressive connection patterns.

## SOCKS5 Support

httpx has native SOCKS5 via httpcore. For advanced cases, use `httpx-socks`:

```python
# Native (httpx >= 0.25)
client = httpx.AsyncClient(proxy="socks5://user:pass@proxy:1080")

# Via httpx-socks (more control over transport)
from httpx_socks import AsyncProxyTransport
transport = AsyncProxyTransport.from_url("socks5://user:pass@proxy:1080")
client = httpx.AsyncClient(transport=transport)
```

Install: `uv add httpx-socks[asyncio]`

## Sticky Session Implementation

### ProxyManager Pattern

```python
"""Extend existing proxy.py with session stickiness."""
from __future__ import annotations
import random
from dataclasses import dataclass, field

@dataclass
class ProxySession:
    proxy_url: str
    user_agent: str
    company_slug: str

class ProxyManager:
    """Assigns one sticky proxy session per company scrape run."""

    def __init__(self, proxy_urls: list[str]) -> None:
        self._pool = proxy_urls
        self._active: dict[str, ProxySession] = {}

    def get_session(self, company_slug: str) -> ProxySession:
        """Get or create a sticky session for a company."""
        if company_slug not in self._active:
            self._active[company_slug] = ProxySession(
                proxy_url=random.choice(self._pool),  # noqa: S311
                user_agent=random_user_agent(),
                company_slug=company_slug,
            )
        return self._active[company_slug]

    def release(self, company_slug: str) -> None:
        """Release session after run completes — next run gets fresh IP."""
        self._active.pop(company_slug, None)
```

### Integration with Existing Scraper

```python
# In orchestrator.py — each adapter gets a sticky client
session = proxy_manager.get_session(company.slug)
async with httpx.AsyncClient(
    proxy=session.proxy_url,
    headers={"User-Agent": session.user_agent},
    limits=httpx.Limits(max_connections=10),
    timeout=httpx.Timeout(30.0),
    http2=False,  # see TLS section below
) as client:
    result = await adapter.scrape(company, db_session, client)
proxy_manager.release(company.slug)
```

## Proxy Provider Comparison

| Type | Detection Risk | Speed | Cost | Session Duration | Use Case |
|---|---|---|---|---|---|
| **Residential** | Low | ~1-3s | $5-15/GB | 1-30 min sticky | ATS sites with bot detection |
| **ISP (static residential)** | Low | ~0.5-1s | $2-5/IP/mo | Unlimited | Long-running scrape jobs |
| **Datacenter** | High | ~0.1-0.3s | $0.5-2/IP/mo | Unlimited | Low-protection targets |

**Recommendation for CompGraph:** Residential proxies with 10-minute sticky sessions. iCIMS and Workday are enterprise ATS platforms — datacenter IPs are likely fingerprinted.

## Error Handling

```python
async def scrape_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_retries: int = 3,
    proxy_manager: ProxyManager,
    company_slug: str,
) -> httpx.Response:
    for attempt in range(max_retries):
        try:
            resp = await client.get(url)
            if resp.status_code == 403:
                raise httpx.HTTPStatusError("Blocked", request=resp.request, response=resp)
            return resp
        except (httpx.ProxyError, httpx.ConnectError) as exc:
            if attempt == max_retries - 1:
                raise
            # Proxy failed — rotate to new IP for remaining requests
            proxy_manager.release(company_slug)
            new_session = proxy_manager.get_session(company_slug)
            # Note: must create a NEW client — proxy is immutable after init
            raise ProxyRotationNeeded(new_session) from exc
```

**Key insight:** httpx `proxy` is immutable after client creation. If you need to rotate mid-session (proxy failure), you must create a new `AsyncClient` instance.

## Anti-Detection Headers

```python
def scraper_headers(user_agent: str) -> dict[str, str]:
    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        # Do NOT set Referer for first request — real browsers don't
    }
```

## Gotchas & Limitations

| Issue | Detail |
|---|---|
| **TLS fingerprinting** | httpx uses Python's `ssl` module — JA3 hash differs from real browsers. For sites with JA3 detection, consider `curl_cffi` instead. iCIMS/Workday likely do NOT check JA3 (they use standard ATS platforms, not custom anti-bot). |
| **HTTP/2 fingerprint** | `http2=True` in httpx uses hyper/h2 — detectable via SETTINGS frame analysis. Keep `http2=False` (the default) unless the target requires it. |
| **Proxy immutability** | Cannot change `proxy` after `AsyncClient` init. Mid-session rotation requires a new client. |
| **env var leak** | `AsyncClient` reads `HTTPS_PROXY`/`HTTP_PROXY` env vars automatically. Set `proxy=""` explicitly to disable if env has proxy vars you don't want. |
| **Connection reuse** | httpx keeps connections alive by default. With sticky proxies this is good — same TCP connection through same proxy IP. |
| **SOCKS5 DNS** | `socks5://` resolves DNS locally; `socks5h://` resolves via proxy. Use `socks5h://` if proxy provider offers geo-DNS. |
| **Rate limiting** | Proxy doesn't bypass rate limits — you still need `asyncio.sleep()` between requests. Combine with existing scraper delays. |

## Migration Path (Existing Scrapers)

1. `proxy.py` already provides `get_proxy_client_kwargs()` — extend, don't replace
2. Add `ProxyManager` class to `proxy.py`
3. Modify `orchestrator.py` to create per-company `AsyncClient` with sticky session
4. Pass `client` to `adapter.scrape()` (requires `ScraperAdapter` protocol update)
5. Adapter isolation preserved — each company still gets its own independent client

Sources:
- [HTTPX Proxies Documentation](https://www.python-httpx.org/advanced/proxies/)
- [HTTPX Transports](https://www.python-httpx.org/advanced/transports/)
- [HTTPX Resource Limits](https://www.python-httpx.org/advanced/resource-limits/)
- [httpx-socks on PyPI](https://pypi.org/project/httpx-socks/)
- [curl_cffi — Browser TLS Impersonation](https://github.com/lexiforest/curl_cffi)
- [Sticky vs Rotating Proxies Guide](https://www.joinmassive.com/blog/sticky-vs-rotating-proxies)
- [Residential vs Datacenter Proxies ROI 2026](https://dev.to/wisdomudo/residential-vs-datacenter-proxies-for-web-scraping-which-one-delivers-better-roi-in-2026-17j0)
- [Web Scraping with HTTPX — BrightData](https://brightdata.com/blog/web-data/web-scraping-with-httpx)
- [ScrapeOps httpx Proxy Rotation](https://scrapeops.io/python-web-scraping-playbook/python-httpx-proxy-rotation/)
