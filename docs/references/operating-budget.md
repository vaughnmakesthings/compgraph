# CompGraph Operating Budget Reference

> Last updated: 2026-02-23

## Infrastructure (Fixed Monthly)

| Line Item | Tier | Cost/mo | Notes |
|-----------|------|---------|-------|
| Digital Ocean Droplet | s-1vcpu-2gb, sfo3 | ~$12 | Backend API + APScheduler. Regular tier, 1 vCPU / 2 GB RAM |
| Supabase | Pro | $25 | Free tier pauses after inactivity — production requires Pro. Includes 8 GB DB |
| Supabase compute overage | (usage) | $0–15 | Compute add-ons start at $10/mo if shared CPU is a bottleneck |
| Vercel | Hobby | $0 | Internal B2B tool easily stays within hobby limits (100 GB bandwidth) |
| GitHub | Free | $0 | Actions minutes well within free tier (2,000 min/mo) |
| Domain registration | compgraph.io + compgraph.app | ~$3 | ~$10–20/yr each via Porkbun, annualized |
| Cloudflare DNS | Free | $0 | Both domains behind Cloudflare |
| SSL certificates | Free | $0 | Caddy via Let's Encrypt |
| **Infrastructure subtotal** | | **~$40–55/mo** | |

## LLM / Enrichment (Variable)

2-pass enrichment pipeline: Haiku 4.5 (Pass 1: classification + pay extraction) + Sonnet 4.5 (Pass 2: entity extraction).
Steady-state net-new posting intake ~30–60/day across 5 companies.

### Pricing Reference (as of Feb 2026)

| Model | Input | Output | Batch (50% off) |
|-------|-------|--------|-----------------|
| Claude Haiku 4.5 | $1.00/M tokens | $5.00/M tokens | $0.50/$2.50 |
| Claude Sonnet 4.5 | $3.00/M tokens | $15.00/M tokens | $1.50/$7.50 |

Sources: [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)

### Monthly LLM Estimates

| Scenario | Cost/mo |
|----------|---------|
| Steady state, no Batch API | $6–15 |
| Steady state, with Batch API (50% discount) | $3–7 |
| Heavy backfill / dev reruns (no dedup) | up to $110 |
| M6 target (batch + dedup + arq) | $10–20 |

## Total Operating Cost

| Scenario | Monthly |
|----------|---------|
| Current steady state | ~$50–70 |
| Unoptimized ceiling (backfill runs) | ~$150 |
| M6 optimized target | ~$55–75 |

## Future / Scaling Items

| Line Item | Trigger | Est. cost |
|-----------|---------|-----------|
| DO Droplet upgrade (s-2vcpu-4gb) | Scheduler contention under load | +$12–18/mo |
| Redis on DO (for arq job queue) | M6 arq migration | +$15/mo |
| Supabase compute add-on | Slow agg table queries | +$10–50/mo |
| Vercel Pro | Team growth or bandwidth spike | +$20/user/mo |
| GitHub Teams | Private repo or more CI minutes | +$4/user/mo |

## Data Enrichment — Prospects Section (Currently Mock)

If the Sales Prospects section is built out with real data:

| Service | Purpose | Est. cost |
|---------|---------|-----------|
| Apollo.io | Contact finding (title, email, LinkedIn) | $49–149/mo |
| Clay | Automated prospect enrichment workflows | $149–800/mo |
| LinkedIn Sales Navigator | Decision-maker identification | $99/user/mo |
| Crunchbase / PitchBook | Company revenue and funding intel | $29–99/mo |

These are optional — only relevant if CompGraph expands to actual outreach tooling.

## Monitoring / Ops (Optional)

| Line Item | Cost |
|-----------|------|
| Sentry (error tracking) | $0 free / $26 developer |
| Grafana Cloud / DataDog | $0–35/mo |
| Uptime monitoring | $0–10/mo |

## Key Optimization Levers

1. **Anthropic Batch API** — 50% discount, planned for M6. No quality tradeoff.
2. **Enrichment deduplication** — skip re-enriching postings with no changes (tracked via `enrichment_version`)
3. **Prompt caching** — for repeated system prompts; 90% discount on cache reads
4. **LiteLLM fallback** — route cheaper tasks to Gemini Flash / Mistral, planned for M6

## Action Items

- [ ] Confirm current Supabase plan (free vs. Pro) — free tier pauses on inactivity
- [ ] Enable Anthropic Batch API in M6
- [ ] Add spend alert in Anthropic dashboard at $50/mo
- [ ] Track LLM cost per run in `enrichment_runs` table
