# Supabase Auth Setup Runbook

Supabase project: `tkvxyxwfosworwqxesnz` (us-west-2)
Dashboard: https://supabase.com/dashboard/project/tkvxyxwfosworwqxesnz

## Dashboard Configuration

### 1. Email Provider

**Auth > Providers > Email**

- Email + password sign-in: **enabled**
- Magic link sign-in: **enabled**
- Confirm email: **enabled** (users must verify email before access)

### 2. URL Configuration

**Auth > URL Configuration**

| Setting | Value |
|---------|-------|
| Site URL | `https://compgraph.vercel.app` |
| Redirect URLs | `https://compgraph.vercel.app/setup`, `http://localhost:3000/setup` |

When adding new environments, add their `/setup` callback to the redirect allow-list.

### 3. Disable Public Sign-Up

**Auth > Settings**

- "Allow new users to sign up": **disabled**

This enforces invite-only access. New users are created via `POST /api/v1/admin/invite` which calls the Supabase Admin API with the service role key.

### 4. Collect Secrets

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
