# Research

Structured codebase or web research with explicit scope boundaries. Prevents unbounded exploration sessions.

## Input

Required: topic description (e.g., "how Workday CXS pagination works", "Supabase connection pooling options")

## Constraints

- **MAX 5 tool calls** for the exploration phase (Glob, Grep, Read, WebSearch, WebFetch)
- If 5 calls don't yield a clear answer, stop and summarize what was found + what's still unknown
- Do not open more than 3 files in a single research pass

## Steps

1. **Scope** — before any tool calls, write a 1-sentence research question and identify 2-3 likely sources (files, URLs, search terms)

2. **Explore** (max 5 tool calls) — gather information from codebase or web

3. **Synthesize** — produce structured output in this format:
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

4. **Save** — write findings to `docs/references/<topic-slug>.md`

5. **Commit** — stage and commit the reference doc:
   ```bash
   git add docs/references/<topic-slug>.md
   git commit -m "docs: add research on <topic>"
   ```

## Rules

- Always produce the structured output even if research is inconclusive
- Do not spiral into tangential exploration — stay on the stated research question
- If the topic requires more than 5 tool calls, report findings so far and ask the user whether to continue
