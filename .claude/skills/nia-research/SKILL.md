---
name: nia-research
description: Deep research using Nia Oracle and Deep Research for complex multi-source questions
---

# /nia-research

Deep research using Nia's Pro research tools. For questions that span multiple libraries, need comparative analysis, or require synthesis from documentation + source code.

## Input

Required: research question (e.g., "How should we implement connection pooling with asyncpg and SQLAlchemy for Supabase?", "Compare APScheduler v4 async job store options")

## When to Use

Use `/nia-research` instead of `/research` when:
- Question spans 2+ libraries that need cross-referencing
- Bleeding-edge APIs are involved (APScheduler v4, Next.js 16, React 19)
- You need verified code patterns from actual source code, not hallucinated APIs
- Migration or upgrade decisions need comparative analysis

Use `/research` instead when:
- Question is about CompGraph internals (CodeSight is better)
- Question is about current events, pricing, or non-code topics (WebSearch is better)
- Simple single-library lookup (just use `nia_package_search_hybrid` directly)

## Credit Budget

| Tool | Credits | Use When |
|------|---------|----------|
| `nia_package_search_hybrid` | 1 | Single-library semantic question |
| `search` | 1 | Cross-source semantic search |
| `nia_deep_research_agent` | 5 | Multi-step research with synthesis |
| Oracle (`nia_research` mode=oracle) | 10 | Complex autonomous discovery |

**Default:** Start with `nia_deep_research_agent` (5 credits). Escalate to Oracle only if Deep Research is insufficient.

## Steps

1. **Check prior research** — avoid re-spending credits:
   ```
   context(action="search", query="<topic keywords>")
   ```
   Also check claude-mem: `search(query="<topic>", project="compgraph")`

2. **Verify index coverage** — ensure relevant packages are indexed:
   ```
   list_repositories()
   ```
   If a critical source is missing, index it first (1 indexing job).

3. **Choose research depth:**

   **Quick (1-2 credits):** Single-library API clarification
   ```
   nia_package_search_hybrid(registry="py_pi", package_name="sqlalchemy", semantic_queries=["async session connection pooling"])
   ```

   **Standard (5 credits):** Multi-source synthesis
   ```
   nia_deep_research_agent(query="How to implement async connection pooling with SQLAlchemy 2.0 and asyncpg for Supabase Postgres with session-mode pooler")
   ```

   **Deep (10 credits):** Complex architecture question needing autonomous discovery
   ```
   nia_research(query="...", mode="oracle")
   ```
   Reserve for questions worth the cost — migration strategies, major architecture decisions.

4. **Produce structured output:**

   ```markdown
   ## Nia Research: <topic>

   **Credits spent:** X (tool used: deep_research/oracle/package_search)

   ### Summary
   1-2 sentence answer.

   ### Key Findings
   - Finding 1 — source: <package/file/url>
   - Finding 2 — source: <package/file/url>

   ### Code Examples
   ```python/typescript
   # Verified pattern from actual library source
   ```

   ### CompGraph Application
   How this applies to our specific stack and constraints.

   ### Caveats
   Version-specific notes, uncertainty, or areas needing validation.
   ```

5. **Persist findings** (dual save — always do both):
   ```
   # Nia context (cross-agent, cross-editor)
   context(action="save", key="research:<topic-slug>", content="<findings>")

   # Claude-Mem (cross-session)
   save_memory(text="Nia Research: <topic> — <key finding>", project="compgraph")
   ```

6. **Save to file** — write to `docs/references/<topic-slug>.md`

7. **Commit:**
   ```bash
   git add docs/references/<topic-slug>.md
   git commit -m "docs: nia research on <topic>"
   ```

## Rules

- NEVER hallucinate an API — if Nia returns no results, say so
- ALWAYS cite which source a finding came from
- Start at 5-credit depth, escalate to 10 only if needed
- Don't re-research topics already in Nia context — build on prior findings
- Track cumulative credit spend in output for budget awareness
- If the question is better answered by CodeSight (CompGraph internals), redirect — don't waste credits
