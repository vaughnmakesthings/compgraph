# PRD → Task Decomposition & Sprint Planning

> LLM-optimized reference for turning product requirements into implementable sprint tasks.

---

## 1. Decomposition Hierarchy

```
PRD → Epics → User Stories → Tasks → Sub-tasks
```

| Level | Scope | Size | Example |
|-------|-------|------|---------|
| **Epic** | Major feature area | 1-4 weeks | "Acosta JobSync scraper integration" |
| **User Story** | Single user-facing capability | 2-5 days | "As a user, I can see Acosta job postings in the dashboard" |
| **Task** | One implementable unit | 0.5-2 days | "Implement JobSync API adapter with pagination" |
| **Sub-task** | Atomic code change | 1-4 hours | "Add `fetch_page()` method to JobSync adapter" |

**Rule:** If a task takes >2 days, decompose further. If <2 hours, merge with related tasks.

---

## 2. INVEST Criteria (Story Quality Gate)

Every story entering a sprint must pass:

| Criterion | Question | Fail Signal |
|-----------|----------|-------------|
| **I**ndependent | Can it be built without waiting on other stories? | Blocked by unmerged PR |
| **N**egotiable | Is scope flexible (not a rigid spec)? | Over-specified implementation |
| **V**aluable | Does it deliver user or business value? | Pure refactor with no outcome |
| **E**stimable | Can the team estimate effort? | Too many unknowns → spike first |
| **S**mall | Fits in one sprint? | Multi-week story |
| **T**estable | Clear pass/fail criteria? | "Make it better" |

---

## 3. Vertical vs Horizontal Slicing

**Always prefer vertical slices** — cut through the full stack so each slice is independently deployable and testable.

```
WRONG (horizontal):                 RIGHT (vertical):
┌─────────────────────┐            ┌──────┐ ┌──────┐ ┌──────┐
│      Frontend       │            │ UI   │ │ UI   │ │ UI   │
├─────────────────────┤            │ API  │ │ API  │ │ API  │
│        API          │            │ DB   │ │ DB   │ │ DB   │
├─────────────────────┤            │      │ │      │ │      │
│      Database       │            │Slice1│ │Slice2│ │Slice3│
└─────────────────────┘            └──────┘ └──────┘ └──────┘
```

**CompGraph natural vertical slices:**
- Scraper adapter (adapter + DB models + tests)
- Enrichment pass (prompt + extraction + entity resolution + tests)
- Aggregation table (SQL rebuild + API endpoint + frontend chart)
- API endpoint (route + query + schema + tests)

---

## 4. Spike Tasks (Uncertainty Resolution)

When a story has significant unknowns, create a **time-boxed spike** first:

```
Spike: Research JobSync API authentication     [1 day max]
Output: findings doc + refined implementation stories
```

**Spike triggers:**
- New external API with no documentation
- Unfamiliar technology or library
- Performance concern with unknown magnitude
- Architecture decision with multiple viable paths

**Spike output must include:** Decision made, alternatives rejected (with reasons), refined task list.

---

## 5. Acceptance Criteria Format

Every task needs explicit "done when" conditions. Two formats:

**Checklist (preferred for tasks):**
```markdown
## Acceptance Criteria
- [ ] JobSync adapter fetches all pages for a single agency
- [ ] Postings are persisted to `postings` + `posting_snapshots`
- [ ] Duplicate detection works via external_id
- [ ] Unit tests cover pagination, error handling, empty response
- [ ] `uv run pytest -x` passes with no regressions
```

**Given/When/Then (for user-facing stories):**
```markdown
GIVEN the scraper pipeline runs
WHEN Acosta agencies are included in the schedule
THEN new Acosta postings appear in the posting explorer within 24 hours
```

---

## 6. Spec-Driven Development (GitHub Spec Kit Pattern)

Modern 4-phase workflow optimized for AI-assisted development:

| Phase | Input | Output | Agent Role |
|-------|-------|--------|------------|
| **Specify** | Goal + problem context | PRD with acceptance criteria, edge cases | AI asks clarifying questions |
| **Plan** | PRD | Technical decisions, file paths, dependencies | AI proposes architecture |
| **Tasks** | Plan | Ordered task list with acceptance criteria | AI decomposes into bounded units |
| **Implement** | Tasks | Code, tests, PR | AI executes sequentially or in parallel |

**Key insight:** The PRD isn't a guide for implementation — it's the source that *generates* implementation. Each task maps back to a specific PRD section.

---

## 7. Sprint Planning Workflow

### Pre-Sprint (Decomposition)
1. Select candidate issues from backlog
2. Apply INVEST criteria — reject or split stories that fail
3. Create spikes for high-uncertainty items
4. Decompose stories into tasks with acceptance criteria
5. Identify file overlaps and dependency ordering

### Sprint Execution (CompGraph-specific)
1. `/sprint-plan` — build file-overlap matrix, assign merge waves
2. Wave N: `/worktree` per issue → implement → `/draft-pr`
3. When wave ready: `/draft-pr ready` → `/pr-feedback-cycle` → `/merge-guardian`
4. After wave merges: rebase next wave on main, repeat

### Task Ordering Rules
- **Dependencies first** — DB migration before API endpoint before frontend
- **High-risk first** — uncertain tasks early in sprint (time to recover)
- **Shared files last** — tasks touching the same files in later waves (avoid conflicts)

---

## 8. Common Decomposition Antipatterns

| Antipattern | Problem | Fix |
|-------------|---------|-----|
| Horizontal slicing | "Build all DB tables" then "build all APIs" — nothing works until everything works | Vertical slices |
| Gold plating | Adding features not in the PRD | Strict acceptance criteria |
| Mega-task | "Implement scraper" (3+ days) | Split by adapter method or pipeline stage |
| Micro-task | "Add import statement" (<1 hour) | Merge into parent task |
| Missing spikes | Estimating unknowns as known work | Time-box research first |
| No acceptance criteria | "Make it work" — ambiguous done state | Write criteria before coding |
| Technical-only stories | "Refactor X" with no user value | Tie to user outcome or label as tech debt |

---

## 9. Task Template

```markdown
## Task: [Short descriptive title]

**Parent:** #[issue-number] [epic/story title]
**Estimate:** [0.5d | 1d | 2d]
**Files:** [list of files to create/modify]

### Description
[1-2 sentences: what and why]

### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Tests pass: `uv run pytest -x -q`
- [ ] Lint passes: `uv run ruff check src/ tests/`

### Dependencies
- Requires: [task/PR that must merge first]
- Blocks: [tasks waiting on this]

### Technical Notes
[Optional: key decisions, patterns to follow, gotchas]
```

---

## Sources

- [From PRD to Tasks: The Art of Decomposition](https://www.signlz.co/from-prd-to-tasks-the-art-of-decomposition)
- [GitHub Spec Kit: Spec-Driven Development](https://github.com/github/spec-kit)
- [INVEST Criteria — Agile Alliance](https://agilealliance.org/glossary/invest/)
- [Humanizing Work: Splitting User Stories](https://www.humanizingwork.com/the-humanizing-work-guide-to-splitting-user-stories/)
- [Addy Osmani: How to Write a Good Spec for AI Agents](https://addyosmani.com/blog/good-spec/)
- [Martin Fowler: Spec-Driven Development Tools](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
