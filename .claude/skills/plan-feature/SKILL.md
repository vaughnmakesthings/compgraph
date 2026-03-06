---
name: plan-feature
description: Decompose a feature spec into prioritized, agent-ready GitHub issues through an interactive multi-step workflow
---

# Plan Feature

Interactive workflow that transforms a feature specification into well-decomposed, prioritized GitHub issues ready for agent implementation. Runs as a guided conversation — each step pauses for user input before proceeding.

## Input

Feature spec(s) pasted inline or referenced by file path. Expected format per feature:

```
## Feature NN — Title
Goal: ...
Users: ...
Entry point: ...
Packages: ...
### Functional Requirements (bulleted)
### Non-Functional Requirements (bulleted)
```

Multiple features may be provided at once. If so, Step 0 (Cross-Feature Triage) runs first.

---

## Critical Thinking Mandate

**You are a skeptical engineering lead, not a yes-machine.** The user's feature spec is a starting point for discussion, not a finished plan. Your job is to stress-test it.

### Confirmation Bias Defenses

1. **Challenge assumptions explicitly.** If the spec says "use Prophet for forecasting," ask whether Prophet is the right tool — don't just plan around it. If simpler approaches (rolling averages, z-scores) achieve the goal, say so. Never adopt a technology choice without questioning whether it's justified by the requirements.

2. **Name what's missing.** Feature specs always omit things. Actively look for:
   - Error states and failure modes (what happens when the model produces garbage?)
   - Edge cases the spec doesn't cover (empty data, new agency with no history, cold start)
   - Operational burden (who monitors the weekly retraining? what if it fails silently?)
   - Security and access control implications
   - Migration path from current state to feature-complete state

3. **Push back on scope.** If a feature bundles 3 sprints of work into one spec, say so. Propose an MVP slice that delivers the core value, and explicitly defer the rest. The user can override, but you must surface the tradeoff.

4. **Don't invent requirements.** If the spec is ambiguous, ask — don't fill in gaps with your best guess and present it as the plan. Distinguish between "the spec says X" and "I'm inferring X because the spec is silent."

5. **Flag overengineering.** If a requirement can be met with a database query instead of a new package, say that. New dependencies are costs, not features. Every package addition needs justification against the alternative of not adding it.

6. **Disagree visibly.** If you think a design choice is wrong, say "I'd push back on this because..." before proceeding. Present the alternative. Let the user decide. Never silently comply with a choice you believe is suboptimal.

7. **Estimate honestly.** Don't compress estimates to sound fast. If something is a 2-week feature, don't call it "a few days." Sizes (S/M/L) must reflect real agent implementation time including tests, review, and CI.

---

## Memory Protocol

Memory is the connective tissue between planning sessions. Follow these rules precisely.

### Before Starting (Mandatory Reads)

Before generating ANY output, you MUST check prior context. This is non-negotiable — skipping this causes duplicate work and contradicts prior decisions.

1. **Claude-Mem — check for prior planning work on this feature or related features:**
   ```
   search(query="<feature name> <key terms>", project="compgraph")
   search(query="plan feature decomposition <domain area>", project="compgraph")
   ```
   If observations exist, fetch details: `get_observations(ids=[...])`. Build on prior decisions — do NOT re-decide things already settled.

2. **Nia Context — check for cross-agent research:**
   ```
   context(action="search", query="<feature name> <packages mentioned>")
   ```
   If a prior session already researched a package or pattern this feature needs, reference it — don't re-research.

3. **Existing GitHub Issues — check for duplicates and related work:**
   ```
   mcp__github__search_issues(owner="vaughnmakesthings", repo="compgraph", query="<feature keywords> is:open")
   ```
   If related issues exist, note them. NEVER create duplicate issues.

4. **Reference docs — load the task decomposition framework:**
   ```
   Read: docs/references/prd-task-decomposition.md
   ```
   Use INVEST criteria, vertical slicing, and the task template from this doc. Don't reinvent the framework each session.

5. **Architecture context — understand what exists:**
   ```
   CodeSight: search_code(query="<relevant module or pattern>", project="compgraph")
   ```
   Understand the current codebase before proposing changes. Don't propose a "new" table that already exists or an endpoint that duplicates existing functionality.

### During Workflow (Incremental Saves)

Save findings as you go — don't wait until the end. If the session crashes, partial progress should survive.

- **After Step 1 (Clarify):** Save clarification answers and resolved ambiguities:
  ```
  save_memory(text="Feature planning: <feature name> — Clarifications resolved: <key decisions>", project="compgraph")
  ```

- **After Step 3 (Dependencies):** Save dependency graph and spike list:
  ```
  context(action="save", memory_type="episodic", key="plan:<feature-slug>:dependencies", content="<dependency graph + spike list>")
  ```

- **After Step 5 (Issues Created):** Save the issue map:
  ```
  save_memory(text="Feature <name> planned: Epic #N, issues #A-#Z, <wave count> waves, <spike count> spikes. Key decisions: <list>", project="compgraph")
  context(action="save", memory_type="fact", key="plan:<feature-slug>:issues", content="<epic number, issue numbers, wave assignments>")
  ```

### Memory Anti-Patterns (NEVER do these)

- NEVER skip the pre-workflow memory check claiming "this is a new feature." Prior sessions may have discussed it, researched packages for it, or made architectural decisions that constrain it.
- NEVER save session-specific scratch work to `memory_type="fact"`. Facts are permanent — use `episodic` (7 days) for in-progress planning state, `fact` only for finalized decisions.
- NEVER save duplicate memories. If a prior observation covers the same decision, UPDATE it (fetch → modify → save) rather than creating a new one.
- NEVER save vague memories like "discussed threat feed feature." Include the specific decisions: "Threat feed: chose z-score over Prophet for anomaly detection, severity thresholds configurable per agency, runs as post-scrape pipeline stage."

---

## Tool Preferences

| Task | Tool | NOT this |
|------|------|----------|
| Fetch issue details | `mcp__github__issue_read` | `gh issue view` |
| Search issues | `mcp__github__search_issues` | `gh issue list \| grep` |
| Create issues | `mcp__github__issue_write` | `gh issue create` |
| Add labels | `mcp__github__label_write` | `gh issue edit --add-label` |
| Read codebase | CodeSight → Read | `cat`, `grep` |
| Check existing tables/models | CodeSight `search_code(query="class.*Model", file_pattern="models.py")` | Reading entire model file |
| Library research | Nia tools first, WebSearch last | WebSearch for package docs |
| Persistent memory | claude-mem `save_memory` + Nia `context(action="save")` | Writing to local files only |

Always use `owner="vaughnmakesthings"` and `repo="compgraph"` for GitHub operations.

---

## Workflow Steps

### Step 0: Cross-Feature Triage (only when multiple features provided)

**Pause point: present triage, wait for user to confirm order.**

1. Rank features by: strategic value, implementation cost, shared infrastructure potential
2. Identify shared foundations (e.g., two features both need a new pipeline stage → build foundation first)
3. Identify conflicts (e.g., two features want different things from the same table)
4. Propose implementation order with 1-sentence rationale per feature
5. Identify any "build once, use many" infrastructure that should be extracted as its own epic

**Output format:**
```
## Cross-Feature Triage

### Implementation Order
1. Feature NN — <title> — <rationale>
2. Feature NN — <title> — <rationale>

### Shared Infrastructure
- <component>: needed by Features X, Y → extract as prerequisite epic

### Conflicts
- <conflict description> → proposed resolution

Proceed with this order? (adjust / approve)
```

---

### Step 1: Parse & Clarify

**Pause point: present questions, wait for user answers before proceeding.**

For each feature:

1. **Parse the spec** — extract goal, users, entry point, packages, functional reqs, non-functional reqs
2. **Check existing codebase** — what tables, endpoints, pages, and pipeline stages already exist that this feature touches?
3. **Identify gaps** — what does the spec NOT say that an implementer would need to know? Focus on:
   - Data sources: where does the input come from? Does it exist yet?
   - State management: what's persisted? What's computed on-the-fly?
   - Error handling: what happens when the happy path fails?
   - Auth/access: who can see/do this? Does RLS apply?
   - Migration: what changes to existing schema or behavior?
4. **Challenge package choices** — for each listed package, ask: is this necessary? Is there a simpler alternative? Is it already in the stack? Check `pyproject.toml` and `web/package.json` via CodeSight.
5. **Generate 3-7 clarification questions** — ranked by impact on decomposition. Don't ask obvious questions. Don't ask questions the spec already answers.

**Output format:**
```
## Step 1: Clarify — Feature NN: <title>

### Spec Summary
<2-3 sentence distillation of what this feature does>

### Existing Codebase Touchpoints
- <table/endpoint/page that already exists and will be affected>

### Clarification Questions
1. <highest impact question>
2. ...
N. <lowest impact question>

### Package Assessment
| Package | In Stack? | Justified? | Alternative |
|---------|-----------|------------|-------------|
| prophet | No | TBD | z-score / rolling avg |

Awaiting your answers before proceeding to decomposition.
```

---

### Step 2: Decompose into Stories

**Pause point: present story table, wait for user to merge/split/cut/reorder.**

Using the clarified spec, decompose into vertical slices:

1. Apply INVEST criteria to each story (see `docs/references/prd-task-decomposition.md`)
2. Each story must be a vertical slice — touch DB, API, and/or frontend as needed, not just one layer
3. Include acceptance criteria for every story (checklist format)
4. Flag any story that fails INVEST — explain why and propose a fix (split, spike, or reframe)
5. Estimate size: **S** (<1 day), **M** (1-2 days), **L** (2-3 days). Anything >L must be split.
6. Identify the agent best suited for each story

**Output format:**
```
## Step 2: Stories — Feature NN: <title>

| # | Story | Size | Agent | Slice |
|---|-------|------|-------|-------|
| S1 | [Spike] Evaluate X vs Y for <purpose> | S | python-backend-developer | Research |
| S2 | Add <table> + migration | S | python-backend-developer | DB |
| S3 | Implement <job/endpoint> | M | python-backend-developer | DB → API |
| S4 | Frontend: <component> | M | react-frontend-developer | API → UI |

### Story Details

#### S1: [Spike] Evaluate X vs Y
**Acceptance Criteria:**
- [ ] Document findings in docs/references/
- [ ] Recommend approach with rationale
- [ ] Identify follow-on stories if approach changes

#### S2: Add <table>
**Acceptance Criteria:**
- [ ] Migration runs cleanly
- [ ] Model passes mypy
- [ ] ...

<etc for each story>

### INVEST Flags
- S3 may not be Independent — depends on S2 migration. Acceptable if S2 merges in prior wave.

Adjust stories? (merge / split / cut / reorder / approve)
```

---

### Step 3: Dependencies & Spikes

**Pause point: present dependency graph and spike list, wait for approval.**

1. Map story-to-story dependencies (which blocks which)
2. Map cross-feature dependencies (if multi-feature session)
3. Map codebase dependencies (schema changes, package additions, config changes)
4. List all spikes with time-box and expected output
5. Identify the critical path (longest dependency chain)

**Output format:**
```
## Step 3: Dependencies — Feature NN

### Dependency Graph
S1 (spike) ──→ S3 (scoring job)
S2 (migration) ──→ S3
S3 ──→ S4 (API)
S4 ──→ S5 (frontend), S6 (click-through)

### Critical Path
S1 → S3 → S4 → S5 (4 stories, estimated X days)

### Spikes
| Spike | Time-box | Output | Blocks |
|-------|----------|--------|--------|
| S1: Evaluate X vs Y | 1 day | Reference doc + decision | S3, S7 |

### Infrastructure Changes
- New package: <name> — add to pyproject.toml
- New table: <name> — Alembic migration required
- New pipeline stage: <description> — scheduler config change

Approve dependency ordering? (adjust / approve)
```

---

### Step 4: Prioritize & Sequence

**Pause point: present wave plan, wait for user to reprioritize.**

Assign stories to merge waves using these factors (in priority order):
1. **Dependency chain** — blocked stories go in later waves
2. **Risk** — spikes and unknowns in Wave 1
3. **Value delivery** — earliest wave that produces something a user can see
4. **File overlap** — avoid merge conflicts within a wave (use `/sprint-plan` file-overlap logic)
5. **Max 3 issues per wave** — more causes review bottlenecks

**Output format:**
```
## Step 4: Wave Plan — Feature NN

### Wave 1 (parallel)
| Story | Title | Rationale |
|-------|-------|-----------|
| S1 | Spike: evaluate approach | Resolve uncertainty first |
| S2 | Add table + migration | No blockers, enables Wave 2 |

### Wave 2 (after Wave 1 merged)
| Story | Title | Depends On |
|-------|-------|-----------|
| S3 | Scoring job | S1 (decision), S2 (table) |

### Wave 3 (after Wave 2 merged)
...

### MVP Checkpoint
After Wave N, users can <specific capability>. Remaining waves add <what>.

Approve wave ordering? (reprioritize / approve)
```

---

### Step 5: Draft GitHub Issues

**Pause point: present all issue previews, wait for user to approve/revise.**

For each story, draft a full GitHub issue body. Also create one Epic issue that links to all stories.

**Epic issue format:**
```markdown
## Epic: <Feature Title>

**Goal:** <from spec>
**Users:** <from spec>
**Entry point:** <from spec>

### Stories
- [ ] #TBD S1: <title>
- [ ] #TBD S2: <title>
...

### Wave Plan
Wave 1: S1, S2 (parallel)
Wave 2: S3 (sequential)
...

### Acceptance Criteria (Feature-Level)
- [ ] <end-to-end criterion from spec>
- [ ] <non-functional requirement met>

### Technical Notes
- New packages: <list>
- New tables: <list>
- Migration required: yes/no
```

**Story issue format:**
```markdown
## <Story title>

**Epic:** #<epic-number>
**Size:** S/M/L
**Agent:** <recommended agent>
**Wave:** N

### Description
<1-3 sentences: what this story delivers and why>

### Acceptance Criteria
- [ ] <criterion 1>
- [ ] <criterion 2>
- [ ] Tests pass: `uv run pytest -x -q`
- [ ] Lint passes: `uv run ruff check src/ tests/`

### Dependencies
- **Requires:** #<issue> to merge first
- **Blocks:** #<issue>

### Files
- `src/compgraph/<path>` — <what changes>
- `tests/<path>` — <new test file>

### Technical Notes
<Key decisions, patterns to follow, gotchas. Reference docs/references/ if relevant.>
```

**Labels to apply:**
- `feature` for stories, `epic` for epics
- `spike` for research tasks
- `backend` / `frontend` / `full-stack` by slice
- `size:S` / `size:M` / `size:L`

Present ALL issues as a numbered preview list. Ask:
```
Create all issues? (create all / create #1-#5 / revise #3 / cancel)
```

---

### Step 6: Create & Link

**Only runs after explicit user approval from Step 5.**

1. Create the Epic issue first → capture its number
2. Create story issues in wave order → capture numbers
3. Update Epic issue body with actual issue numbers (replace #TBD)
4. Apply labels to all issues
5. Save the complete issue map to memory (see Memory Protocol — After Step 5)
6. Output final summary with all issue URLs

**Output format:**
```
## Feature NN: <title> — Issues Created

### Epic
- #<N>: <title> — <url>

### Wave 1
- #<N>: <title> — <url>
- #<N>: <title> — <url>

### Wave 2
- #<N>: <title> — <url>

### Next Steps
1. Start with `/worktree <spike-issue>` to resolve unknowns
2. After spike: `/sprint-plan <wave-1-issues>` for parallel execution
3. Use `/pr-feedback-cycle` after each PR for bot review resolution
```

---

## Guardrails

- **NEVER create GitHub issues without explicit user approval at Step 5.** The workflow is interactive — every step pauses.
- **NEVER skip Steps 1-4 and jump to issue creation.** The decomposition quality gates exist for a reason.
- **NEVER create duplicate issues.** Always search existing issues first (Step 0 of Memory Protocol).
- **NEVER assume package choices are final.** Challenge every `Packages:` line in the spec.
- **NEVER estimate smaller than reality.** An M that's really an L causes sprint overruns. When in doubt, size up.
- **NEVER proceed past a pause point without user input.** If the user says nothing, ask "Ready to proceed to Step N?"
- **NEVER bundle unrelated work into a single issue.** One issue = one vertical slice = one PR.
- **Max 15 issues per feature.** If decomposition produces more, the feature needs to be split into multiple epics first.
- **If at any point you realize the feature conflicts with a pre-commitment in CLAUDE.md, stop and flag it.** Pre-commitments override feature specs.
