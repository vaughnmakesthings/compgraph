# Metabase OSS Evaluation for CompGraph Frontend

**Date:** 2026-02-20
**Research question:** Is Metabase OSS a viable alternative to the planned Next.js custom frontend (M7)?

## Key Findings

1. **Supabase + Metabase works out of the box** — Supabase has official docs for connecting Metabase directly to Postgres. Self-hosted via Docker on a DO Droplet is straightforward.

2. **OSS tier is severely limited for user-facing use** — Free tier only supports "guest embedding" (iframes without SSO, no drill-through, no data segregation, no advanced theming). The React Embedding SDK for proper Next.js integration is Pro/Enterprise only ($12/user/month).

3. **Customization ceiling is low** — Even on paid tiers, Metabase embeds look like Metabase. Theming limited to colors/fonts. Always feels like a third-party tool, not a native experience.

4. **Custom SQL queries supported in OSS** — Raw SQL works, so our aggregation tables could be queried directly.

5. **No programmatic control** — Dashboards configured via Metabase UI, not code. No dashboard-as-code, no version control of views, no CI/CD for frontend layer.

## Relevance to CompGraph

### Where Metabase shines
- Rapid prototyping — could replace Streamlit immediately without waiting for M7
- Direct Postgres connection queries aggregation tables today
- Self-hosted on DO Droplet fits infra plan
- Non-technical users can explore data without code

### Where it falls short
- M7 requires AG Grid (complex data tables), Recharts (custom viz), role-based route protection — OSS can't do these
- Invite-only magic link auth via Supabase Auth requires paid SDK or hacky iframe workarounds
- No export/PDF control beyond Metabase native capabilities
- CompGraph is a product for internal stakeholders — custom views need tailored UX

## Recommendation

**Don't replace M7. Use Metabase as a bridge tool during M4-M6:**

- Deploy Metabase OSS alongside the API during M4 as an ad-hoc exploration tool — zero dev effort, immediate value for leadership
- Keep Next.js custom frontend as the M7 production target (custom tables, auth, export, branding)
- Re-evaluate during M5 — if Metabase covers 80% of use cases, M7 scope could shrink

## OSS vs Pro Feature Comparison (relevant to CompGraph)

| Feature | OSS (Free) | Pro ($12/user/mo) |
|---------|-----------|-------------------|
| Direct Postgres queries | Yes | Yes |
| Custom SQL | Yes | Yes |
| Basic dashboards | Yes | Yes |
| Guest embedding (iframe) | Yes | Yes |
| React Embedding SDK | No | Yes |
| Drill-through on embeds | No | Yes |
| SSO integration | No | Yes |
| Data segregation/RBAC | No | Yes |
| Advanced theming | No | Yes |
| White-label | No | Enterprise only |

## Open Questions

- Would leadership accept Metabase's native UI, or do they expect a branded product?
- Is $12/user/month Pro tier viable for proper embedding + SSO?
- Could Metabase handle "explore" views while Next.js handles operational dashboards?

## Sources

- [Supabase: Connecting to Metabase](https://supabase.com/docs/guides/database/metabase)
- [Metabase Embedding Introduction](https://www.metabase.com/docs/latest/embedding/introduction)
- [Metabase OSS Editions](https://www.metabase.com/start/oss/)
- [Metabase Pricing](https://www.metabase.com/pricing/)
- [Metabase on Docker](https://www.metabase.com/docs/latest/installation-and-operation/running-metabase-on-docker)
- [Embeddable vs Metabase comparison](https://embeddable.com/blog/embeddable-vs-metabase)
