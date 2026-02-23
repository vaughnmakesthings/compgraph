# Auto-Deploy on Merge to Main — Design

**Date:** 2026-02-21
**Status:** Approved

## Context

Automatically deploy the CompGraph Eval dashboard to the Raspberry Pi whenever code is merged to `main`. The Pi is LAN-only (192.168.1.69) but runs Tailscale (`devserver.tailc6b3c4.ts.net`, IP `100.102.42.5`).

## Approach: Tailscale + GitHub Actions

### Workflow

A GitHub Actions workflow (`.github/workflows/deploy.yml`) that:

1. Triggers on push to `main` branch
2. Installs Tailscale on the runner using `tailscale/github-action`
3. Authenticates with an OAuth client secret (ephemeral node, auto-removed after workflow)
4. SSHs to the Pi via Tailscale network
5. Runs deploy steps: `git pull`, `npm ci`, `npm run build`, symlink static assets, fix ownership, restart service, health check

### Secrets Required

| Secret | Purpose |
|--------|---------|
| `TAILSCALE_AUTHKEY` | Tailscale OAuth client secret for ephemeral runner nodes |
| `PI_SSH_KEY` | SSH private key authorized on the Pi's root user |

### Security

- Tailscale auth key creates ephemeral nodes (auto-removed after workflow completes)
- SSH key is scoped to deploy operations
- Workflow only triggers on `main` branch pushes
- Concurrency group prevents parallel deploys

### Relationship to CI

A CI workflow already exists on `feat/frontend-dx` (lint, typecheck, test, build, a11y). The deploy workflow runs separately — it triggers only on push to main (post-merge), not on PRs.

## Rejected Alternatives

- **Self-hosted runner on Pi**: Extra service to maintain, security exposure
- **Claude Code hook**: Only works from local machine, not GitHub UI merges
- **Webhook receiver**: Requires exposing an endpoint via Tailscale Funnel
