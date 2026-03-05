# 1Password / Secrets Reference

All secrets managed via 1Password. Never hardcode.

| Env Var | 1Password Reference | Used By |
|---------|-------------------|---------|
| `DATABASE_URL` | `op://DEV/SUPABASE_COMPGRAPH_DBPW/password` (embedded in connection string) | SQLAlchemy async engine (session mode pooler) |
| `DATABASE_URL_DIRECT` | `op://DEV/SUPABASE_COMPGRAPH_DBPW/password` (embedded in connection string) | Alembic migrations (direct connection) |
| `ALEMBIC_DATABASE_URL` | Full asyncpg connection string (optional override) | Alembic only — use pooler URL when direct host DNS fails |
| `ANTHROPIC_API_KEY` | `op://DEV/ANTHROPIC_API_KEY/credential` | LLM enrichment (Haiku + Sonnet) |
| `SUPABASE_URL` | `op://DEV/COMPGRAPH_SUPABASE/url` | Supabase client (if used directly) |
| `SUPABASE_KEY` | `op://DEV/COMPGRAPH_SUPABASE/anon-key` | Supabase client (if used directly) |
| `SUPABASE_ACCESS_TOKEN` | 1Password: `SUPABASE_ACCESS_TOKEN` | Supabase MCP server (`.mcp.json`), Management API |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` (default, no auth) | Redis cache (optional, `None` if not configured) |

> **Note:** `SUPABASE_ACCESS_TOKEN` is configured in 1Password. Update remaining references above with actual vault paths once connection strings are generated. Project ID: `tkvxyxwfosworwqxesnz`, DB host: `db.tkvxyxwfosworwqxesnz.supabase.co`.

### Proxy Provider (optional — for residential proxy rotation)

| Env Var | 1Password Reference | Used By |
|---------|-------------------|---------|
| `PROXY_URL` | `op://DEV/{PROVIDER}_PROXY/url` | Proxy server URL (e.g. `http://proxy.example.com:8080`) |
| `PROXY_USERNAME` | `op://DEV/{PROVIDER}_PROXY/username` | Proxy authentication username |
| `PROXY_PASSWORD` | `op://DEV/{PROVIDER}_PROXY/credential` | Proxy authentication password |

When configured, both iCIMS and Workday adapters route all HTTP requests through the proxy. Credentials are embedded in the proxy URL automatically via `Settings.proxy_url_with_auth`. User-agent strings are rotated per-scrape from a curated browser UA pool.

### Usage

```bash
# Local: load secrets and run
eval $(op signin)
op run --env-file=.env -- uv run compgraph

# Or populate .env from template (gitignored)
op inject -i .env.example -o .env

# Run migrations with secrets (direct connection)
op run --env-file=.env -- uv run alembic upgrade head

# If direct host DNS fails (IPv6 issue), use pooler URL override:
ALEMBIC_DATABASE_URL="postgresql+asyncpg://..." op run --env-file=.env -- uv run alembic upgrade head

# Run tests (DATABASE_URL has fallback in conftest.py)
uv run pytest
```

For GitHub Actions, use `1password/load-secrets-action@v2` with `OP_SERVICE_ACCOUNT_TOKEN` repo secret.

**Debugging**: `launchctl setenv` for system-wide env vars. Verify with `env | grep OP_`. MCP servers need env vars inherited from parent process.
