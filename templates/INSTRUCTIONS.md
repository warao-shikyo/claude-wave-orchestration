# Plan operation rules

Drop this into your project's plans folder (e.g. `.claude/plans/INSTRUCTIONS.md`). Every session reads this on launch.

This file matches the **session-orchestrator** / **session-master** skills. Where the two differ, the skills win.

## Vocabulary

- **plan**: a Markdown file describing one piece of work (`<area>-<NNN>-<slug>.md`)
- **area**: a lowercase domain word that prefixes the plan id (`auth`, `billing`, `ui`, `api`, `infra`, `docs`, …). The `meta-` area is reserved for orchestration-meta plans.
- **status**: where the plan is in its lifecycle (see below)
- **wave**: a batch of plans being worked on in parallel
- **worktree**: an isolated working directory for one plan (`.worktrees/<area>-<NNN>/`)
- **orchestrator**: the session coordinating all the others; runs in the main project directory
- **session master**: a session launched by the orchestrator to work one plan in its own worktree

## Naming convention (area-prefix scheme)

| Element | Form | Example |
|---|---|---|
| plan file | `<area>-<NNN>-<slug>.md` | `auth-001-oauth-login.md` |
| done file | `<area>-<NNN>-<slug>_done.md` | `auth-001-oauth-login_done.md` |
| branch | `plan/<area>-<NNN>` | `plan/auth-001` |
| worktree | `.worktrees/<area>-<NNN>/` | `.worktrees/auth-001/` |
| commit | `<type>(plan-<area>-<NNN>): …` | `feat(plan-auth-001): …` |
| docs spec | `docs/specs/<area>-<NNN>-<slug>.md` | |

- `area` is a lowercase word for the system/domain. **Do not distinguish systems by number band** — humans can't memorize "the 500s are billing." Use the area prefix instead.
- The `meta-` area is for orchestration-meta plans only (e.g. `meta-001-wave3-planning.md`).
- Define the project's area list at the top of `_progress.md`.

## Plan status lifecycle

```
draft → ready → in_progress → done | cancelled | blocked
```

| Status | Meaning | How it's expressed |
|---|---|---|
| `draft` | Just created, not ready for execution | `## Status` line |
| `ready` | Worktree-ready, awaiting session launch | `## Status` line |
| `in_progress` | Session active, working the plan | `## Status` line |
| `done` | Plan complete | **rename the file to `<id>-<slug>_done.md`** |
| `cancelled` | Plan no longer relevant (reason required) | `## Status` line + reason in execution log |
| `blocked` | Stuck on external dependency (reason required) | `## Status` line + reason in execution log |

**Done is expressed by the filename, not the Status line.** When a plan is complete, `git mv` it to `<id>-<slug>_done.md` and commit it. `cancelled` / `blocked` stay as `## Status` edits with a recorded reason (they are not renamed).

## Plan MD structure

Each plan MD must include:

```markdown
# {area}-{NNN}-{slug} — {Title}

## Status
{draft|ready|in_progress|cancelled|blocked}
<!-- done is expressed by renaming the file to ..._done.md, not here -->

## Purpose
Why this plan exists. Plain prose.

## Background
Context. What's the situation that requires this.

## Scope
What's in scope.

## Out of scope
What's NOT in scope (important — sets boundaries).

## Completion criteria
Objective tests that say "this plan is done":
- [ ] criterion 1
- [ ] criterion 2
- [ ] existing test suite still green (no regression)
- [ ] verified manner: <unit | integration | manual | NOT VERIFIED — deferred to test Wave>

The `verified manner` line is mandatory and must be honest. Shipping
`NOT VERIFIED — deferred to test Wave` is allowed; silently claiming "done"
without verification is not. A later test Wave picks up the deferred items —
see [test-waves.md](../patterns/test-waves.md).

## Related
Links to other plans, memory entries, docs.

## Execution log
Append-only. Each entry: date + what happened.
```

The execution log is **mandatory**. It's the audit trail.

## Landing responsibility for session masters

A session master carries one plan from launch to a terminal state **and commits its work** — that is the full extent of its landing authority.

| Action | Allowed? |
|---|---|
| Implement the plan | ✅ on its own judgment |
| Ask the user directly | ✅ |
| **commit** (to `plan/<id>`) | ✅ **this is the end of its responsibility** |
| **push** | ❌ forbidden (user's call) |
| **open a PR** | ❌ forbidden (user's call) |
| **merge to main** | ❌ forbidden (user's call) |
| deploy (for verification) | ⚠️ from the worktree, on its own judgment, if needed (see below) |
| edit another worktree | ❌ forbidden |

**Why commit-only**: if each master pushes / merges on its own, code rolls back when branches collide. Push / merge / production rollout are **all left to the user (the master themself)**. Your output stays as commits on the `plan/<id>` local branch.

A session master also:

- **Owns its plan** from start to terminal state (`done`/`cancelled`/`blocked`)
- **Updates its own plan MD** (status + execution log)
- **Updates its own row in `_progress.md`** (in the worktree copy), stamping `last_activity` (HH:MM) at checkpoints — start, after each commit, when asking the user a blocking question, and at completion (see [session-monitoring.md](../patterns/session-monitoring.md))
- **Reports deploy status** honestly: `none` (committed, not deployed), `verified-on-deploy` (deployed only to verify), or `live`. Don't claim something runs in production just because the code exists in a branch (see [ANTI-PATTERNS.md #11](../ANTI-PATTERNS.md#11-we-didnt-establish-whats-the-production-reality-baseline))

A session master must NOT:

- **push, open PRs, or merge to main** (all user decisions)
- **Edit other plans' worktrees**
- **Touch `.gitignore` to remove `.worktrees/`** (we want worktrees ignored)
- **Make scope decisions outside its plan** (escalate to user or note as "out of scope")

### Deploy (only when verification needs it)

If verifying the work requires a deploy, you **may deploy from the worktree on your own judgment** (follow the project's deploy procedure). This is for verification only and is separate from git push / merge. Record the result honestly in the completion summary's `deploy:` field (`none` / `verified-on-deploy` / `live`).

## commit convention

```
<type>(plan-<id>): <description>     e.g. feat(plan-auth-001): add OAuth login
```

## Dependency handling

If your plan depends on another plan that's not yet done:

1. Check if the other plan is in a `plan/<id>` branch — you can fetch and reference it
2. If you're truly blocked, set status to `blocked` and record `blocked on plan-<id>` in the execution log
3. The orchestrator will reassign or wait

## Worktree conventions

```
Path:    .worktrees/<area>-<NNN>/
Branch:  plan/<area>-<NNN>
Base:    integration/latest-known-good  (origin/main only on Wave 1)
```

The `.worktrees/` directory is in `.gitignore`. Do not commit it.

## Completion procedure

When your plan's completion criteria are met:

1. Record the final result (evidence for done / commit hash) in the plan MD's execution log.
2. **Rename the file to `_done`** and commit:
   ```bash
   git mv .claude/plans/<id>-<slug>.md .claude/plans/<id>-<slug>_done.md
   git commit -m "chore(plan-<id>): mark done"
   ```
3. Emit the **completion summary** (below). Include the key terminal output (test results, build output, etc.).
4. **Always spell out new issues / residual work** — don't swallow them. The orchestrator files them into the backlog.

### Completion summary format (two sections)

```
=== Detailed summary (for the user to read) ===
[Can be long. The user reads it for situational awareness.
 Cover: what changed, verification, key terminal output (test/build),
 discoveries, new issues, residual work, out-of-scope notes.]

=== Short summary (for the orchestrator — user pastes this) ===
plan <id> → done|cancelled|blocked
commit: <hash> (push: no — commit is the end of responsibility)
verified: unit|integration|manual|deferred
deploy: none|verified-on-deploy|live
done-file: <id>-<slug>_done.md
key: <~30-char take-away>
new-issues: <new issues, 0-3 lines>
residual: <residual work, 0-3 lines>
```

The user reads the detailed section themselves and pastes only the short section to the orchestrator.

## When to call it `cancelled` instead of `done`

You may judge `cancelled` when:

- Plan's premise no longer holds (architecture shift, requirements changed)
- Plan is duplicated by another plan with equivalent scope
- Implementation cost is much higher than expected and value is unclear (escalate first, but cancellation is a valid outcome)

Set `## Status` to `cancelled` and record the reason in the execution log. Do **not** rename to `_done`.

## When to call it `blocked`

You may judge `blocked` when:

- Waiting on external party (vendor approval, partner integration)
- Waiting on another plan that's been assigned to a different session
- Tool / environment issue you can't resolve

Set status `blocked`, record what's blocking, and stop. Don't loop.

## Out-of-scope bugs

Don't fix them yourself (unless they block your own plan). Record them in the execution log and write them up in the completion summary's `new-issues` field as a new-plan proposal. The orchestrator files them into the backlog.

## Out of context before the plan is done

Save your progress in the execution log, set status back to `ready` with a note on where you stopped, and stop. **Don't push** (your commits stay local). The orchestrator spawns a follow-up session.

## Notes about `_progress.md`

- The master `_progress.md` lives in the orchestrator's working directory only
- Each worktree gets a **read-only snapshot** at launch
- You may edit the snapshot in your worktree (it helps your own bookkeeping) but the orchestrator will re-apply your change to the master
- **Do not** try to merge `_progress.md` from branches — it's operational state, not source code. Better yet, your project's `.gitignore` should exclude it from any session's commits.

## Common questions

**Q: Should I push or open a PR?**
No. A session master's responsibility ends at `commit`. push / PR / merge are the user's call.

**Q: I found a bug not in my plan's scope. What do I do?**
Document it (execution log + as a new-plan suggestion in the `new-issues` field). Don't fix it unless it's blocking your own plan.

**Q: My plan turned out to be impossible / wrong / done already. What do I do?**
Set status appropriately (`cancelled`, or rename to `_done` for implicit done), write reasoning, and stop. Don't fight the plan.

**Q: I need help from another session.**
You can't talk to other sessions directly. Either ask the user, or annotate your plan as `blocked on plan-<id>` and stop.

**Q: I'm out of context and the plan isn't done.**
Save progress in the execution log, set status back to `ready` with notes on where you stopped. Don't push (commits stay local). The orchestrator can spawn a follow-up session.
