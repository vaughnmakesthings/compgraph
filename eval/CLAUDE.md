# CLAUDE.md — compgraph-eval

LLM evaluation tool for CompGraph enrichment prompts. Compares prompt versions, measures field accuracy, and visualizes quality regressions.

## Project Structure

```
compgraph-eval/
├── web/              # Next.js 16 dashboard (React 19, Tailwind v4, Recharts)
├── scripts/          # Python eval scripts + git hooks
├── tests/            # Python tests (pytest)
├── infra/            # Pi deployment (systemd unit, deploy script)
└── docs/             # Plans and design docs
```

## Commands

### Frontend (web/)

```bash
cd web
npm run dev              # Dev server (localhost:3000)
npm run build            # Production build (catches RSC boundary errors)
npm run lint             # ESLint strict (--max-warnings 0)
npm run lint:fix         # ESLint with auto-fix
npm run typecheck        # TypeScript --noEmit
npm test                 # Vitest run
npm run test:watch       # Vitest watch mode
npm run test:coverage    # Vitest with v8 coverage enforcement
```

### Python (eval scripts)

```bash
uv sync                  # Install dependencies
uv run pytest            # Run Python tests
uv run ruff check scripts/
uv run ruff format scripts/
```

### Git Hooks

```bash
bash scripts/setup-hooks.sh    # Install pre-commit + pre-push hooks
```

- **pre-commit**: ESLint + tsc (frontend), ruff check + format (Python)
- **pre-push**: Vitest (frontend), pytest (Python); skipped for docs-only changes

## Deployment

### Raspberry Pi (Local Dev Server)

The eval dashboard runs on a Raspberry Pi at `192.168.1.69`, accessible on LAN and via Tailscale.

- **SSH**: `ssh compgraph-dev` (root@192.168.1.69)
- **URL**: `http://192.168.1.69:3000` (LAN), also reachable via Tailscale hostname `devserver`
- **Auto-deploy**: Merging to `main` triggers `.github/workflows/deploy-pi.yml` → Tailscale SSH to Pi → pull, build, restart
- **Manual deploy**: `bash infra/deploy-eval-pi.sh`
- **Manual trigger**: `gh workflow run deploy-pi.yml --ref main`
- **Service**: `systemctl {start|stop|restart|status} compgraph-eval`
- **Logs**: `journalctl -u compgraph-eval -f`
- **App path**: `/opt/compgraph-eval/web/` (Next.js standalone output)
- **Node.js**: v22.22.0 LTS

### Deploy Pipeline

```
Push to main → GitHub Actions → Tailscale (ephemeral OAuth node) → SSH to Pi → git pull → npm ci → npm run build → symlink static assets → systemctl restart → health check
```

### Infrastructure Files

| File | Purpose |
|------|---------|
| `infra/compgraph-eval.service` | systemd unit — runs standalone Next.js on port 3000 as `compgraph-eval` user |
| `infra/deploy-eval-pi.sh` | Manual deploy script — SSH to Pi, pull, build, restart, health check |
| `.github/workflows/deploy-pi.yml` | GitHub Actions auto-deploy via Tailscale on push to main |

### GitHub Secrets

| Secret | Purpose |
|--------|---------|
| `TS_OAUTH_CLIENT_ID` | Tailscale OAuth client ID (scopes: `auth_keys` + `devices`, tag: `tag:ci`) |
| `TS_OAUTH_SECRET` | Tailscale OAuth client secret |

### Tailscale

The Pi is connected to a Tailscale mesh network for remote access from GitHub Actions.

- **Tailnet**: `tailc6b3c4.ts.net`
- **Pi hostname**: `devserver` (IP: `100.102.42.5`, tagged `tag:server`)
- **Tailscale SSH**: Enabled on Pi — CI nodes with `tag:ci` can SSH as root
- **ACL rule**: `tag:ci` → `tag:server` SSH accept
- **API token**: `TAILSCALE_TOKEN` in 1Password DEV vault (for ACL management via API)
- **Admin console**: https://login.tailscale.com/admin
- **API example**: `curl -H "Authorization: Bearer $(op item get TAILSCALE_TOKEN --vault DEV --fields token)" https://api.tailscale.com/api/v2/tailnet/tailc6b3c4.ts.net/acl`

## Stack

- **Next.js 16** / **React 19** / **TypeScript 5**
- **Tailwind CSS v4** (CSS-first config via `@theme` in `globals.css`)
- **Recharts 3** — chart components in `web/src/components/ui/`
- **Radix UI** — primitives (Sheet, Tooltip, Separator)
- **Vitest 4** + **Testing Library** + **vitest-axe** — testing with accessibility
- **ESLint 9** (flat config) + **eslint-config-next**

## Test Conventions

- Test files: `src/**/*.test.{ts,tsx}` or `src/app/<route>/__tests__/page.test.tsx`
- Use `@/__tests__/helpers/render` for wrapped render (providers, router mocks)
- Every page test includes an accessibility check via `vitest-axe`
- Coverage: 50% minimum (lines/functions/statements), 30% minimum (branches)
- Coverage excludes `components/ui/` (vendor-adapted Tremor/shadcn) and `hooks/`

## Design Tokens

All colors, spacing, and typography are defined as CSS custom properties in `web/src/app/globals.css` using Tailwind v4's `@theme` directive. Components use Tailwind utility classes that reference these tokens — **never hardcode hex values in component files**.

Allowed exceptions:
- `globals.css` (token definitions)
- `chart-utils.ts` (Recharts color map)
- `components/ui/` (shadcn-generated, uses Tailwind classes)

## PR Workflow

Before pushing any branch:
1. `npm run lint` — ESLint strict mode
2. `npm run typecheck` — TypeScript check
3. `npm test` — full test pass
4. Only push after all three pass

## Frontend Design Rules

See `/frontend-design` skill in the `compgraph` repo. Key rules:
- No purple/indigo/violet primary colors (AI-generation tell)
- No gradient hero sections
- No glassmorphism on cards
- No uniform large border-radius everywhere
- No `transition-all` — specify exact properties
- Use project design tokens, not hardcoded values
