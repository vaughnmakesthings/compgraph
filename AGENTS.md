# CompGraph — Agent Guide

Primary project context: [CLAUDE.md](CLAUDE.md)

## Agent Crew

Project agents in `.claude/agents/`:
- `python-backend-developer` — enrichment, aggregation, API, general backend
- `scraper-developer` — ATS adapter implementation, scraper debugging, HTTP/parsing, data verification
- `react-frontend-developer` — Next.js, Recharts, AG Grid, Vitest
- `nextjs-deploy-ops` — DO deployment, Caddy, systemd, Supabase RLS
- `code-reviewer` — plan alignment, async patterns, append-only rules
- `pytest-validator` — test audit
- `spec-reviewer` — scope gate
- `database-optimizer` — query/index/schema
- `agent-organizer` — multi-agent orchestration and delegation
- `security-reviewer` — auth, RLS, input validation, injection risks
- `production-debugger` — full-stack production incident investigation (Vercel + Sentry + Supabase + browser)
- `dx-optimizer` — developer tooling, build performance, workflow automation
- `enrichment-monitor` — enrichment pipeline health, data quality diagnostics
- `python-pro` — Python refactoring & optimization only (no new features — use python-backend-developer for implementation)
- `aggregation-specialist` — aggregation job debugging, rollup validation, drift detection, new aggregation job implementation

Review sequence: implement → code-reviewer → pytest-validator → spec-reviewer

## Learned User Preferences

<!-- Populated by continual-learning skill from transcript mining -->

## Learned Workspace Facts

<!-- Populated by continual-learning skill from transcript mining -->
