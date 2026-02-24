---
name: schema-change
description: End-to-end schema change workflow — branch isolation, migration, type generation, local verification, deploy, and post-deploy checks
---

# Schema Change Workflow

Orchestrates the full lifecycle of a database schema change: isolated branch → Alembic migration → TypeScript type regeneration → local verification → push → production verification. Composes existing skills (`/migrate`, `/pre-release`, `/deploy`) with Supabase branch isolation and Vercel build checks.

## Input

- `<description>` — brief description of the schema change (used for migration message and branch naming)

## Steps

### 1. Create Supabase Branch (Isolation)

Use Supabase MCP to create an isolated branch database so the migration can be tested without touching production data.

```
supabase: confirm_cost() → acknowledge branch cost
supabase: create_branch(name="schema/<description>", projectId="tkvxyxwfosworwqxesnz")
```

Record the branch ID and connection details for subsequent steps.

> **Skip this step** if the change is trivial (e.g., adding a nullable column) and user confirms they want to apply directly to prod. Ask first.

### 2. Generate Migration

Run the `/migrate generate` workflow against the branch database:

```
/migrate generate <description>
```

This will:
- Run pre-flight checks (include_name filter, 1Password CLI, connectivity)
- Autogenerate the Alembic migration
- Present the diff for user approval

**Review checklist** (in addition to `/migrate`'s built-in checks):
- Does the migration affect aggregation tables? If so, the aggregation rebuild job may need updating
- Does the migration add NOT NULL columns without defaults? This will fail on existing data
- Does the migration touch RLS policies? Flag for security-reviewer

### 3. Apply Migration to Branch

```
/migrate apply
```

Applies pending migrations to the Supabase branch. Verify with `/migrate status`.

### 4. Regenerate TypeScript Types

If the schema change affects tables used by the frontend:

```
supabase: generate_typescript_types(projectId="tkvxyxwfosworwqxesnz")
```

This regenerates `web/src/lib/database.types.ts`. Verify the diff makes sense — new columns, changed types, etc.

### 5. Local Verification

Run `/pre-release` to verify everything compiles and tests pass with the new schema:

```
/pre-release
```

This covers backend lint/typecheck/tests and frontend lint/typecheck/tests/build.

If the dev server is running (`npm run dev` in `web/`), also verify visually:

```
next-devtools: browser_eval → screenshot affected pages
```

Check for:
- TypeScript compilation errors from changed types
- Runtime errors on pages that query changed tables
- Hydration errors from SSR/client data mismatches

### 6. Run Supabase Advisors

Post-migration, check for security and performance issues:

```
supabase: get_advisors(projectId="tkvxyxwfosworwqxesnz")
```

Flag:
- New tables missing RLS policies → must add before deploy
- New columns used in WHERE clauses missing indexes → add index migration
- Any security warnings

### 7. Push and Deploy

Once all checks pass:

```bash
git add alembic/ web/src/lib/database.types.ts
git commit -m "schema: <description>"
git push origin <branch>
```

If deploying backend schema to production:
```
/deploy
```

### 8. Post-Deploy Verification

After push, verify the Vercel build succeeds:

```
vercel: list_deployments(projectId="prj_8IH6w1sFBAbXQhkmr1paJE3Nfrpr", teamId="team_rjCtHfOfITLEggddrnr4bhsI", limit=1)
```

If deployment state is ERROR:
```
vercel: get_deployment_build_logs → diagnose build failure
```

If deployment succeeded, run a quick production health check:
```
/health-check --quick
```

Then check Sentry for new errors:
```
/sentry-check
```

### 9. Cleanup Branch

After confirming production is healthy, delete the Supabase branch to stop billing:

```
supabase: manage branch → delete (or via Supabase dashboard)
```

---

## Abort / Rollback

- **Before push**: Simply delete the migration file and reset the branch. No production impact.
- **After push, Vercel build fails**: Fix the TypeScript errors, push again. The schema migration is already applied but the frontend isn't serving the broken build.
- **After deploy, data issues**: Create a new forward migration to revert the DDL change. **Never** run `alembic downgrade` on Supabase — it's destructive.
- **Supabase branch stuck**: Delete the branch via dashboard. It has no effect on production.

## When to Use

- Adding/removing/altering columns
- Creating new tables
- Adding/modifying indexes
- Changing RLS policies
- Any DDL that affects both backend models and frontend types

## When NOT to Use

- Data-only changes (INSERT/UPDATE) — use `supabase: execute_sql` directly
- Frontend-only changes — no schema change needed
- Alembic configuration changes — edit `alembic/env.py` directly
