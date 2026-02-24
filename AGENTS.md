# CompGraph — Agent Guide

Primary project context: [CLAUDE.md](CLAUDE.md)

## Agent Crew

Project agents in `.claude/agents/`:
- `python-backend-developer` — scrapers, enrichment, aggregation, API
- `react-frontend-developer` — Next.js, Recharts, AG Grid, Vitest
- `nextjs-deploy-ops` — DO deployment, Caddy, systemd, Supabase RLS
- `code-reviewer` — plan alignment, async patterns, append-only rules
- `pytest-validator` — test audit
- `spec-reviewer` — scope gate
- `database-optimizer` — query/index/schema
- `agent-organizer` — multi-agent orchestration and delegation
- `security-reviewer` — auth, RLS, input validation, injection risks

Review sequence: implement → code-reviewer → pytest-validator → spec-reviewer

## Learned User Preferences

<!-- Populated by continual-learning skill from transcript mining -->

## Learned Workspace Facts

<!-- Populated by continual-learning skill from transcript mining -->
