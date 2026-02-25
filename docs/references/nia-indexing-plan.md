# Nia Dependency Indexing Plan for CompGraph

# Nia's package search (nia_package_search_hybrid/grep) works on 3K+ pre-indexed
# packages from PyPI/NPM without manual indexing. The commands below are for
# DOCUMENTATION SITES and REPOS that need explicit indexing.

## Documentation Sites (index_documentation)

# Core backend
index_documentation(url="https://fastapi.tiangolo.com/")                     # 311 pages
index_documentation(url="https://docs.sqlalchemy.org/en/20/")                # 161 pages
index_documentation(url="https://alembic.sqlalchemy.org/en/latest/")         # 23 pages
index_documentation(url="https://apscheduler.readthedocs.io/en/master/")     # 10 pages
index_documentation(url="https://docs.anthropic.com/en/docs")                # indexing (added 2026-02-24)

# Supabase (auth, RLS, client)
index_documentation(url="https://supabase.com/docs/guides")                  # 708 pages

# Frontend
index_documentation(url="https://nextjs.org/docs")                           # 379 pages
index_documentation(url="https://tailwindcss.com/docs")                      # 240 pages
index_documentation(url="https://react.dev")                                 # 177 pages
index_documentation(url="https://recharts.org/en-US/api")                    # indexing (re-indexed 2026-02-24)
index_documentation(url="https://www.radix-ui.com/primitives/docs")          # 43 pages
index_documentation(url="https://www.tremor.so/docs")                        # 51 pages

# Roadmap (geo/map features)
index_documentation(url="https://h3geo.org")                                 # 79 pages
index_documentation(url="https://h3.dev")                                    # 32 pages
index_documentation(url="https://docs.mapbox.com")                           # 2516 pages
index_documentation(url="https://visgl.github.io")                           # 11 pages

# Roadmap (LLM provider abstraction)
index_documentation(url="https://openrouter.ai")                             # 142 pages
index_documentation(url="https://vercel.com")                                # 939 pages

# Other
index_documentation(url="https://radix-ui.com")                              # 60 pages (themes)
index_documentation(url="https://logo.dev")                                  # 26 pages

## GitHub Repos (index_repository)

index_repository(url="https://github.com/agronholm/apscheduler")             # v4 alpha source
index_repository(url="https://github.com/recharts/recharts")                 # v3 source
index_repository(url="https://github.com/supabase/supabase-js")              # JS client source
index_repository(url="https://github.com/anthropics/anthropic-sdk-python")   # Python SDK source
index_repository(url="https://github.com/anthropics/claude-code")            # Claude Code source
index_repository(url="https://github.com/radix-ui/primitives")               # Radix primitives
index_repository(url="https://github.com/radix-ui/themes")                   # Radix themes
index_repository(url="https://github.com/uber/h3")                           # H3 geo library
index_repository(url="https://github.com/mapbox/mapbox-gl-draw")             # Mapbox Draw
index_repository(url="https://github.com/openrouterteam/ai-sdk-provider")    # OpenRouter SDK
index_repository(url="https://github.com/vercel-labs/agent-skills")          # React best practices
index_repository(url="https://github.com/vaughnmakesthings/compgraph")       # CompGraph itself

## Notes

# - Pre-indexed PyPI/NPM packages (fastapi, httpx, beautifulsoup4, pydantic,
#   asyncpg, rapidfuzz, react, next, recharts, etc.) are already
#   searchable via nia_package_search_hybrid/grep WITHOUT manual indexing.
# - Budget: Pro tier allows 50 indexing jobs/month. This plan uses ~32.
# - Re-index monthly or when major version updates drop.
# - Last full audit: 2026-02-24 — all sources ✅ ready, 2 gaps fixed (Anthropic docs, Recharts full API)
# - Duplicates cleaned: 4 doc dupes removed (logo.dev x1, mapbox x1, supabase x2)
