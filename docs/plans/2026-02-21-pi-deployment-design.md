# CompGraph Eval — Raspberry Pi Deployment Design

**Date:** 2026-02-21
**Status:** Approved

## Context

Deploy the CompGraph Eval web dashboard (Next.js 16 + React 19) to the local Raspberry Pi dev server at `192.168.1.69`. The eval tool currently uses static/mock data only — no backend connection needed.

## Pi Server Specs

| Property | Value |
|----------|-------|
| Architecture | aarch64 (ARM64) |
| OS | Debian 13 (trixie) |
| RAM | 8GB (7.2GB available) |
| Disk | 54GB free |
| CPU | 4 cores |
| SSH | `compgraph-dev` (root@192.168.1.69) |
| Existing services | compgraph-dashboard (Streamlit), Docker, Tailscale |
| Node.js | Not installed |

## Approach: Direct Node.js + systemd

### 1. Runtime Setup

Install Node.js 22 LTS via NodeSource apt repo. Single global install — no nvm needed for a single-purpose server.

### 2. Application Layout

```
/opt/compgraph-eval/          # Git clone root
  web/                        # Next.js app
    .next/standalone/         # Production build output
```

### 3. Build Configuration

Enable `output: 'standalone'` in `next.config.ts` for optimized self-contained production builds. The standalone output bundles only the required `node_modules` — no full `npm install` needed at runtime.

### 4. systemd Service

Unit: `compgraph-eval.service`
- ExecStart: `node /opt/compgraph-eval/web/.next/standalone/server.js`
- Port: 3000
- User: `compgraph-eval` (non-root)
- Restart: on-failure
- WorkingDirectory: `/opt/compgraph-eval/web`

### 5. Network Access

- LAN: `http://192.168.1.69:3000`
- Tailscale: accessible via Tailscale hostname (already running)
- No reverse proxy — direct port access for LAN-only use

### 6. Deploy Script

`infra/deploy-eval-pi.sh` in the compgraph-eval repo:
1. SSH to Pi
2. `git pull`
3. `npm ci && npm run build`
4. `systemctl restart compgraph-eval`

## Rejected Alternatives

- **Docker**: Heavier, slower ARM builds, unnecessary isolation for a static mock-data app
- **Local build + rsync**: Cross-arch native module risk, two-machine coordination overhead
