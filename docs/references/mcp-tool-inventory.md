# MCP Server Tool Inventory

> Last updated: 2026-02-24
> Total: ~110 tools across 13 MCP servers

## Sources

Tools come from **5 project-level MCP servers** (`.mcp.json`) and **3 plugin-provided MCP servers** (installed plugins). Some tools referenced in agent definitions (Supabase, Sentry, Vercel, Playwright standalone) are provided directly by their respective MCP servers at runtime and aren't discoverable through deferred tool search — they're only available to agents that explicitly list them.

---

## 1. CodeSight (Semantic Code Search)

**Source:** `.mcp.json` — local Python project (`codesight`)
**Purpose:** AI-powered semantic search over indexed codebases using embeddings + LanceDB.

| Tool | Description |
|------|-------------|
| `mcp__codesight__index_codebase` | Walks the project tree (respecting `.gitignore`), chunks code files, generates embeddings, and stores in LanceDB. Incremental by default — skips unchanged files via SHA-256 hashing. Returns stats (files indexed, chunks created, duration). |
| `mcp__codesight__search_code` | Semantic + keyword search across indexed code. Returns **metadata only** (~40 tokens/result) — chunk IDs, file paths, symbol names, types, line ranges, relevance scores. Supports filters: `symbol_type` (function/class/method), `file_pattern` (directory scope). |
| `mcp__codesight__get_chunk_code` | Retrieves **full source code** for specific chunk IDs from `search_code`. Optional context headers (imports, parent class). Two-stage retrieval saves ~63% tokens vs returning full code for all results. |
| `mcp__codesight__get_indexing_status` | Checks index freshness — last indexed time, commit SHA, total files/chunks, and whether the index is stale. |
| `mcp__codesight__list_indexed_projects` | Lists all indexed projects with summary stats (name, path, chunk count, last indexed time). |
| `mcp__codesight__clear_index` | Clears the index for a project (referenced in agent configs). |

---

## 2. GitHub (Plugin: `github@claude-plugins-official`)

**Source:** Official Claude Code plugin (Go-based Docker image)
**Purpose:** Full GitHub API access — issues, PRs, branches, reviews, search, Copilot delegation.

### Repository Management

| Tool | Description |
|------|-------------|
| `github__create_repository` | Create a new GitHub repo in your account or an organization. Supports private repos and auto-init with README. |
| `github__fork_repository` | Fork a repo to your account or a specified organization. |
| `github__get_file_contents` | Get contents of a file or directory from a repo. Supports specific refs (branches, tags, PR heads). |
| `github__create_or_update_file` | Create or update a single file remotely with a commit message. Requires SHA for updates to prevent overwriting. |
| `github__delete_file` | Delete a file from a repo on a specific branch. |
| `github__push_files` | Push **multiple files** in a single commit to a branch. |

### Branch & Tag Management

| Tool | Description |
|------|-------------|
| `github__create_branch` | Create a new branch from an optional source branch. |
| `github__list_branches` | List all branches with pagination. |
| `github__list_tags` | List git tags with pagination. |
| `github__get_tag` | Get details about a specific git tag. |

### Issues

| Tool | Description |
|------|-------------|
| `github__list_issues` | List issues with filters (state, labels, date, sort order). Cursor-based pagination. |
| `github__issue_read` | Read issue details: `get` (details), `get_comments`, `get_sub_issues`, `get_labels`. |
| `github__issue_write` | Create or update issues. Supports assignees, labels, milestones, state changes with reasons (completed/not_planned/duplicate), and issue types. |
| `github__search_issues` | Full GitHub issue search syntax. Sort by reactions, comments, interactions, dates. |
| `github__add_issue_comment` | Add a comment to an issue (also works for PR general comments). |
| `github__list_issue_types` | List supported issue types for an organization. |
| `github__sub_issue_write` | Manage sub-issues: add, remove, or reprioritize within a parent issue. |
| `github__get_label` | Get details of a specific label. |

### Pull Requests

| Tool | Description |
|------|-------------|
| `github__create_pull_request` | Create a new PR with title, body, head/base branches. Supports drafts and maintainer-can-modify. |
| `github__list_pull_requests` | List PRs with filters (state, base/head branch, sort). |
| `github__search_pull_requests` | Full GitHub PR search syntax. Preferred over `list` when filtering by author. |
| `github__pull_request_read` | Read PR data: `get` (details), `get_diff`, `get_status` (CI checks), `get_files` (changed files), `get_review_comments` (threaded), `get_reviews`, `get_comments`. |
| `github__update_pull_request` | Update PR title, body, state, base branch, draft status, reviewers. |
| `github__update_pull_request_branch` | Sync a PR branch with latest base branch changes. |
| `github__merge_pull_request` | Merge a PR (merge, squash, or rebase). |

### PR Reviews

| Tool | Description |
|------|-------------|
| `github__pull_request_review_write` | Create, submit, or delete PR reviews. Supports APPROVE, REQUEST_CHANGES, COMMENT events. Can create pending reviews for batch comments. |
| `github__add_comment_to_pending_review` | Add line-level or file-level comments to a pending review. Supports multi-line ranges and side selection (LEFT/RIGHT diff). |
| `github__add_reply_to_pull_request_comment` | Reply to an existing review comment thread. |
| `github__request_copilot_review` | Request automated Copilot code review on a PR. |

### Commits & Releases

| Tool | Description |
|------|-------------|
| `github__list_commits` | List commits on a branch/tag/SHA with pagination. Filter by author. |
| `github__get_commit` | Get full commit details including diffs and stats. |
| `github__list_releases` | List releases with pagination. |
| `github__get_latest_release` | Get the most recent release. |
| `github__get_release_by_tag` | Get a specific release by tag name. |

### Search

| Tool | Description |
|------|-------------|
| `github__search_code` | Search code across all GitHub repos using native search engine. Supports language, org, path, and content filters. |
| `github__search_repositories` | Find repos by name, description, topics, stars, language. |
| `github__search_users` | Find users by username, location, followers count. |

### Teams & Identity

| Tool | Description |
|------|-------------|
| `github__get_me` | Get the authenticated user's profile. Useful for discovering username for other API calls. |
| `github__get_teams` | Get teams the user belongs to. |
| `github__get_team_members` | Get member usernames of a specific org team. |

### Copilot Integration

| Tool | Description |
|------|-------------|
| `github__assign_copilot_to_issue` | Assign GitHub Copilot coding agent to an issue. It creates a PR with implementation. |
| `github__create_pull_request_with_copilot` | Delegate a task to Copilot agent to create a PR with implementation. |
| `github__get_copilot_job_status` | Check status of a Copilot agent job and get the resulting PR URL. |

---

## 3. Context7 (Plugin: `context7@claude-plugins-official`)

**Source:** Official Claude Code plugin
**Purpose:** Fetch up-to-date library/framework documentation and code examples from the Context7 database.

| Tool | Description |
|------|-------------|
| `context7__resolve-library-id` | Resolves a library name to a Context7-compatible ID (format: `/org/project`). Returns matching libraries ranked by name match, reputation, snippet coverage, and benchmark score. **Must call before `query-docs`** unless user provides an explicit library ID. Max 3 calls per question. |
| `context7__query-docs` | Retrieves documentation and code examples for a library using its Context7 ID. Supports version-specific queries (`/org/project/version`). Max 3 calls per question. |

---

## 4. Claude-Mem (Plugin: `claude-mem@thedotmack`)

**Source:** Third-party plugin by thedotmack
**Purpose:** Persistent cross-session memory database with semantic search. Observations are stored and retrievable across conversations.

| Tool | Description |
|------|-------------|
| `mcp-search____IMPORTANT` | Meta-tool that documents the **mandatory 3-layer workflow**: search -> timeline -> get_observations. Enforces token-efficient retrieval. |
| `mcp-search__search` | **Step 1**: Search memory by query, project, type, date range. Returns an index with observation IDs (~50-100 tokens/result). Supports `obs_type`, `dateStart`/`dateEnd`, `orderBy`, pagination. |
| `mcp-search__timeline` | **Step 2**: Get temporal context around a result. Pass an `anchor` observation ID (or a query to auto-find one) with `depth_before`/`depth_after` to see surrounding observations. |
| `mcp-search__get_observations` | **Step 3**: Fetch full observation details for filtered IDs. Only call after narrowing results via search/timeline to save tokens. |
| `mcp-search__save_memory` | Save a manual memory/observation for future semantic search. Accepts `text` (required), optional `title` (auto-generated if omitted), and `project` name. |

---

## 5. Sequential Thinking (Built-in Anthropic)

**Source:** Built-in Anthropic MCP server
**Purpose:** Structured multi-step reasoning with branching, revision, and hypothesis verification.

| Tool | Description |
|------|-------------|
| `sequential-thinking__sequentialthinking` | A detailed reasoning tool for dynamic problem-solving. Supports: adjustable thought counts, revision of previous thoughts, branching into alternative paths, hypothesis generation and verification, and uncertainty expression. Useful for breaking down complex problems, planning with room for course correction, and multi-step analysis. |

---

## 6. Fetch (Built-in Anthropic)

**Source:** Built-in Anthropic MCP server
**Purpose:** Fetch web content from URLs.

| Tool | Description |
|------|-------------|
| `claude_ai_fetch__fetch` | Fetches content from a URL. Parameters: `url` (required), `max_length` (default 5000 chars), `start_index` (for pagination through long content), `raw` (return raw HTML instead of extracted text). |

---

## 7. Next.js DevTools

**Source:** MCP server for Next.js development
**Purpose:** Runtime integration with Next.js dev servers, documentation access, browser automation, and upgrade tooling.

| Tool | Description |
|------|-------------|
| `nextjs__init` | Initialize Next.js DevTools context. **Must call at session start** for Next.js work. Resets AI knowledge baseline and establishes documentation-first approach. |
| `nextjs__nextjs_index` | Discover all running Next.js dev servers and their available MCP tools. Auto-discovers servers or accepts explicit `port`. Returns server info, PIDs, and tool schemas. Requires Next.js 16+. |
| `nextjs__nextjs_call` | Execute a specific MCP tool on a running Next.js dev server (e.g., `get_errors`, route listing, cache clearing). Requires port and tool name from `nextjs_index`. |
| `nextjs__nextjs_docs` | Fetch official Next.js documentation by path. **Must first read `nextjs-docs://llms-index` resource** to get correct paths. |
| `nextjs__browser_eval` | Full Playwright browser automation: start/navigate/click/type/fill_form/evaluate JS/screenshot/console messages/drag/upload/close. Supports Chrome, Firefox, WebKit, Edge. Headless or headed mode. |
| `nextjs__enable_cache_components` | Automated migration to Next.js 16 Cache Components mode. Handles config updates, dev server management, error detection via MCP, automated fixing (Suspense boundaries, `"use cache"` directives), and verification. |
| `nextjs__upgrade_nextjs_16` | Guided upgrade to Next.js 16. Runs official codemod first (requires clean git state), then handles remaining manual fixes for async APIs, config migration, React 19 compatibility, etc. |

---

## 8. Claude in Chrome (Browser Extension MCP)

**Source:** Chrome extension MCP server
**Purpose:** Full browser automation via a Chrome extension — visual interaction, DOM access, network monitoring, form filling, and GIF recording.

### Tab Management

| Tool | Description |
|------|-------------|
| `tabs_context_mcp` | **Must call first** each session. Gets info about the current MCP tab group and available tabs. Creates a new tab group if none exists. |
| `tabs_create_mcp` | Creates a new empty tab in the MCP tab group. |
| `switch_browser` | Switch to a different Chrome browser instance. Broadcasts a connection request to all Chrome browsers with the extension. |

### Navigation & Interaction

| Tool | Description |
|------|-------------|
| `navigate` | Navigate to a URL or go forward/back in browser history. |
| `computer` | Full mouse/keyboard interaction: left/right/double/triple click, type text, press keys (with modifiers), scroll, drag, screenshot, wait, zoom (inspect region), scroll-to-element, hover. All actions scoped to a specific tab. |
| `find` | Natural language element finder — search by purpose ("search bar", "login button") or text content. Returns up to 20 matching elements with reference IDs for other tools. |
| `form_input` | Set values in form elements using reference IDs from `read_page`. Handles checkboxes (boolean), selects (option value/text), and text inputs. |

### Page Reading

| Tool | Description |
|------|-------------|
| `read_page` | Get accessibility tree representation of page elements. Filters: `interactive` (buttons/links/inputs only) or `all`. Supports depth limiting and focusing on specific elements via `ref_id`. Max 50K chars default output. |
| `get_page_text` | Extract raw article/text content from a page. Prioritizes main content. Returns plain text without HTML. |

### Debugging

| Tool | Description |
|------|-------------|
| `javascript_tool` | Execute arbitrary JavaScript in page context. Access DOM, window object, page variables. Results returned from last expression (no `return` statement needed). |
| `read_console_messages` | Read browser console messages (log/error/warn). Filter by regex pattern (recommended). Option to clear after reading. Can filter errors-only. |
| `read_network_requests` | Read HTTP network requests (XHR, Fetch, documents, images). Filter by URL pattern. Option to clear after reading. Shows cross-origin requests. |

### Media & Recording

| Tool | Description |
|------|-------------|
| `gif_creator` | Record browser interactions as animated GIFs. Actions: `start_recording`, `stop_recording`, `export` (with visual overlays — click indicators, action labels, progress bar, watermark), `clear`. Quality configurable 1-30. |
| `upload_image` | Upload a screenshot or image to a file input or drag-and-drop target. Supports ref-based (hidden file inputs) or coordinate-based (drag-and-drop) targeting. |
| `resize_window` | Resize browser window to specific dimensions for responsive design testing. |

### Shortcuts

| Tool | Description |
|------|-------------|
| `shortcuts_list` | List all available Chrome extension shortcuts/workflows. |
| `shortcuts_execute` | Execute a shortcut/workflow in a new sidepanel window. Starts execution and returns immediately. |

---

## 9. IDE Integration

**Source:** VS Code / IDE MCP server
**Purpose:** Direct integration with the user's IDE for diagnostics and code execution.

| Tool | Description |
|------|-------------|
| `mcp__ide__getDiagnostics` | Get language diagnostics (errors, warnings) from VS Code. Optional URI filter for specific files; omit for all files. |
| `mcp__ide__executeCode` | Execute Python code in the current Jupyter kernel. State persists across calls. Useful for interactive data exploration. |

---

## 10. Agent-Referenced Servers (Runtime-Only)

These tools are referenced in agent configurations but provided directly by their MCP server connections at runtime. They weren't discoverable via ToolSearch — they're available only to agents that explicitly list them.

### Supabase (`supabase` in `.mcp.json`)

| Tool | Capabilities |
|------|-------------|
| `execute_sql` | Run SQL queries directly against Supabase Postgres |
| `apply_migration` | Apply database migrations |
| `list_migrations` | List applied migrations |
| `list_tables` | List database tables |
| `create_branch` | Create a Supabase database branch |
| `confirm_cost` | Confirm cost for operations |
| `get_advisors` | Get Supabase performance/security advisors |
| `generate_typescript_types` | Generate TypeScript types from DB schema |
| `get_project` | Get project metadata |
| `get_logs` | Fetch Supabase logs |
| `search_docs` | Search Supabase documentation |

### Sentry (`sentry` in `.mcp.json`)

| Tool | Capabilities |
|------|-------------|
| `search_issues` | Search for error issues in Sentry |
| `get_issue_details` | Get full details of a specific Sentry issue |
| `search_events` | Search error events/occurrences |
| `find_organizations` | List Sentry organizations |
| `find_projects` | List Sentry projects |

### Vercel (referenced in agent configs)

| Tool | Capabilities |
|------|-------------|
| `list_deployments` | List Vercel deployments |
| `get_deployment` | Get specific deployment details |
| `get_deployment_build_logs` | Fetch build logs |
| `get_runtime_logs` | Fetch runtime/function logs |
| `get_project` / `list_projects` | Project metadata |
| `list_teams` | List Vercel teams |
| `deploy_to_vercel` | Trigger a deployment |
| `get_access_to_vercel_url` / `web_fetch_vercel_url` | Access Vercel-hosted content |
| `search_vercel_documentation` | Search Vercel docs |

### Playwright (standalone, referenced in agent configs)

| Tool | Capabilities |
|------|-------------|
| `browser_navigate` | Navigate to URLs |
| `browser_snapshot` | Capture page state |
| `browser_click` | Click elements |
| `browser_type` | Type into inputs |
| `browser_take_screenshot` | Capture screenshots |

---

## Summary

| MCP Server | Tool Count | Category |
|------------|-----------|----------|
| **GitHub** (plugin) | ~40 tools | Source control, issues, PRs, reviews, search, Copilot |
| **Claude in Chrome** | ~15 tools | Browser automation, DOM, debugging, recording |
| **Next.js DevTools** | 7 tools | Next.js runtime, docs, browser testing, upgrades |
| **CodeSight** | 5-6 tools | Semantic code search, indexing |
| **Claude-Mem** | 5 tools | Persistent cross-session memory |
| **Context7** | 2 tools | Library documentation retrieval |
| **Sequential Thinking** | 1 tool | Structured multi-step reasoning |
| **Fetch** | 1 tool | Web content fetching |
| **IDE** | 2 tools | VS Code diagnostics, Jupyter execution |
| **Supabase** | ~11 tools | Database management (runtime-only) |
| **Sentry** | ~5 tools | Error monitoring (runtime-only) |
| **Vercel** | ~10 tools | Deployment management (runtime-only) |
| **Playwright** | ~5 tools | Browser automation (runtime-only) |
