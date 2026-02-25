# Supabase Auth Setup Runbook

Supabase project: `tkvxyxwfosworwqxesnz` (us-west-2)
Dashboard: https://supabase.com/dashboard/project/tkvxyxwfosworwqxesnz

## Auth Configuration (via CLI)

Auth settings are managed as code in `supabase/config.toml` and pushed via:

```bash
supabase config push --project-ref tkvxyxwfosworwqxesnz
```

Key settings applied:

| Setting | Value | config.toml key |
|---------|-------|-----------------|
| Site URL | `https://compgraph.vercel.app` | `[auth] site_url` |
| Redirect URLs | `/setup` on Vercel + localhost | `[auth] additional_redirect_urls` |
| Public sign-up | **disabled** (invite-only) | `[auth] enable_signup = false` |
| Email confirmations | **enabled** | `[auth.email] enable_confirmations = true` |

When adding new environments, add their `/setup` callback to `additional_redirect_urls` in `config.toml` and re-push.

### Collect Secrets (manual)

These are read-only project secrets — not configurable via CLI:

**Project Settings > API**

| Secret | Location | 1Password Item |
|--------|----------|----------------|
| JWT Secret | JWT Settings section | "Supabase Auth Keys" in DEV vault |
| `service_role` key | API Keys section | "Supabase Auth Keys" in DEV vault |
| `anon` key | API Keys section | Already stored as `SUPABASE_KEY` |

## Environment Variables

Added in `.env.example` and `config.py`:

```env
SUPABASE_JWT_SECRET=<from dashboard>
SUPABASE_SERVICE_ROLE_KEY=<from dashboard>
AUTH_DISABLED=false
```

Existing (no change):
```env
SUPABASE_URL=https://tkvxyxwfosworwqxesnz.supabase.co
SUPABASE_KEY=<anon key>
```

## Production Safety Guard

`AUTH_DISABLED=true` is blocked when `ENVIRONMENT=production` via a pydantic model_validator in `config.py`. This prevents accidentally deploying with auth bypassed.

## JWT Secret Rotation

1. Generate new JWT secret in Supabase Dashboard (Project Settings > API > JWT Settings)
2. Update 1Password item "Supabase Auth Keys"
3. Update `.env` on dev server: `ssh compgraph-do` then edit `/opt/compgraph/.env`
4. Restart service: `systemctl restart compgraph`
5. **All active sessions are invalidated** — users will need to re-authenticate

## Verification Checklist

After completing dashboard setup:

- [ ] Magic link email sends successfully (test via Supabase Dashboard > Auth > Users > Invite)
- [ ] `SUPABASE_JWT_SECRET` stored in 1Password DEV vault
- [ ] `SUPABASE_SERVICE_ROLE_KEY` stored in 1Password DEV vault
- [ ] Dev server `.env` updated with both values
- [ ] `uv run pytest -x -q --tb=short` passes (new defaults don't break existing tests)

## Auth Chain

This runbook covers issue #206 (configuration prerequisites). Subsequent issues:

- **#207**: Backend JWT middleware + `get_current_user` dependency
- **#208**: Frontend auth pages (login, setup, invite)
- **#209**: Row-Level Security policies
- **#210**: Auth test fixtures and integration tests
