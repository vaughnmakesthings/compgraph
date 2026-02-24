# Nia Dependency Indexing Plan for CompGraph
# Run these commands in a Claude Code session to index all key dependencies.
# Nia's package search (nia_package_search_hybrid/grep) works on 3K+ pre-indexed
# packages from PyPI/NPM without manual indexing. The commands below are for
# DOCUMENTATION SITES and REPOS that need explicit indexing.

## Step 1: Verify what's already indexed
# Run this first to see current state:
#   list_repositories()

## Step 2: Index documentation sites (index_documentation)
# These are the highest-value targets — docs that agents hallucinate most.

# APScheduler v4 alpha — HIGHEST PRIORITY (poorly documented, heavily hallucinated)
index_documentation(url="https://apscheduler.readthedocs.io/en/master/")

# Supabase docs (auth, RLS, client, edge functions)
index_documentation(url="https://supabase.com/docs")

# Next.js 16 docs (App Router, bleeding edge)
index_documentation(url="https://nextjs.org/docs")

# FastAPI docs
index_documentation(url="https://fastapi.tiangolo.com/")

# SQLAlchemy 2.0 docs (async patterns)
index_documentation(url="https://docs.sqlalchemy.org/en/20/")

# Alembic docs
index_documentation(url="https://alembic.sqlalchemy.org/en/latest/")

# Recharts 3 docs (frequently hallucinated chart API)
index_documentation(url="https://recharts.org/en-US/api")

# Tailwind CSS v4 docs
index_documentation(url="https://tailwindcss.com/docs")

# Anthropic SDK docs
index_documentation(url="https://docs.anthropic.com/en/docs")

# Radix UI docs
index_documentation(url="https://www.radix-ui.com/primitives/docs")

# Tremor docs
index_documentation(url="https://www.tremor.so/docs")

## Step 3: Index key GitHub repos (index_repository)
# These give Nia access to actual source code, not just docs.

# APScheduler v4 source — critical for understanding the alpha API
index_repository(url="https://github.com/agronholm/apscheduler")

# Recharts source — v3 has breaking changes from v2
index_repository(url="https://github.com/recharts/recharts")

# Supabase JS client
index_repository(url="https://github.com/supabase/supabase-js")

## Step 4: Verify indexing completion
# Indexing is async — check status:
#   check_repository_status(name="<source-name>")
# Wait for all to complete before relying on them.

## Notes:
# - Pre-indexed PyPI/NPM packages (fastapi, httpx, beautifulsoup4, pydantic,
#   asyncpg, rapidfuzz, playwright, react, next, recharts, etc.) are already
#   searchable via nia_package_search_hybrid/grep WITHOUT manual indexing.
# - The above index_documentation calls are for SUPPLEMENTARY context —
#   getting full docs beyond what's in the package source.
# - Budget: Pro tier allows 50 indexing jobs/month. This plan uses ~14.
# - Re-index monthly or when major version updates drop.
