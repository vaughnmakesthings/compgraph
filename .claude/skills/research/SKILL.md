---
name: research
description: Structured codebase or web research with explicit scope boundaries
---

# Research

Structured codebase or web research with explicit scope boundaries. Prevents unbounded exploration sessions.

## Input

Required: topic description (e.g., "how Workday CXS pagination works", "Supabase connection pooling options")

## Constraints

- **MAX 7 tool calls** for the exploration phase (claude-mem, Nia, CodeSight, Glob, Grep, Read, WebSearch, WebFetch)
- If 7 calls don't yield a clear answer, stop and summarize what was found + what's still unknown
- Do not open more than 3 files in a single research pass

## Steps

1. **Check Memory** — search claude-mem for prior research on this topic BEFORE exploring:
   ```
   search(query="<topic keywords>", project="compgraph")
   ```
   If relevant observations exist, fetch details: `get_observations(ids=[...])`. Skip re-researching what's already known — build on prior findings.

2. **Check Nia Context** — search Nia for prior cross-agent research:
   ```
   context(action="search", query="<topic keywords>")
   ```
   If relevant context exists, retrieve it: `context(action="retrieve", key="<key>")`. Build on prior work.

3. **Scope** — write a 1-sentence research question and identify 2-3 likely sources (files, URLs, search terms). Note what memory/Nia already answered. Classify the question:
   - **Library/framework API question** → use Nia tools (step 4a)
   - **CompGraph implementation question** → use CodeSight (step 4b)
   - **External/current info** → use WebSearch (step 4c)

4. **Explore** (max 5 remaining tool calls) — gather NEW information:

   **4a. Library/API questions (use Nia FIRST):**
   - `nia_package_search_hybrid(registry="py_pi"|"npm", package_name="...", semantic_queries=["..."])` — AI semantic search
   - `nia_package_search_grep(registry="py_pi"|"npm", package_name="...", pattern="...")` — exact pattern match
   - `search(query="...")` — cross-source semantic search
   - `nia_deep_research_agent(query="...")` — for multi-library questions (5 credits)
   - For complex architecture questions, delegate: `Task(agent="nia-oracle", prompt="...")`

   **4b. CompGraph codebase questions (use CodeSight):**
   - `search_code(query="...", project="compgraph")` → `get_chunk_code(chunk_ids)` for source

   **4c. External/current info (use WebSearch last resort):**
   - **WebSearch/WebFetch** for non-code research, pricing, current events

5. **Synthesize** — produce structured output in this format:
   ```
   ## Research: <topic>

   ### Key Findings
   - Finding 1 (with source reference)
   - Finding 2
   - Finding 3

   ### Relevance to CompGraph
   - How this applies to our specific situation

   ### Recommended Actions
   - [ ] Action 1
   - [ ] Action 2

   ### Open Questions
   - Anything unresolved after 5 tool calls
   ```

6. **Save to file** — write findings to `docs/references/<topic-slug>.md`

7. **Save to memory** — persist key findings for future sessions:
   ```
   save_memory(text="Research: <topic> — <key finding summary>", project="compgraph")
   ```

8. **Save to Nia context** — persist for cross-agent access:
   ```
   context(action="save", key="research:<topic-slug>", content="<structured findings>")
   ```

9. **Index** — check if the new reference doc is listed in `docs/context-packs.md` Tier 2 "External Research" table. If not, add a row:
   ```
   | `docs/references/<topic-slug>.md` | <one-line description> | <relevant domain> |
   ```
   Choose the domain based on content: Scraper design, Enrichment pipeline, Database setup, Pipeline debugging, etc.

10. **Commit** — stage and commit the reference doc (and context-packs.md if updated):
    ```bash
    git add docs/references/<topic-slug>.md docs/context-packs.md
    git commit -m "docs: add research on <topic>"
    ```

## Rules

- Always produce the structured output even if research is inconclusive
- Do not spiral into tangential exploration — stay on the stated research question
- If the topic requires more than 5 tool calls, report findings so far and ask the user whether to continue
- **NEVER use WebSearch for library API questions** — Nia has indexed all major CompGraph dependencies
- Save ALL significant findings to both claude-mem AND Nia context for dual persistence
