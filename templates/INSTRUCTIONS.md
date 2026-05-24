# Plan operation rules

Drop this into your project's plans folder (e.g. `.claude/plans/INSTRUCTIONS.md`). Every session reads this on launch.

## Vocabulary

- **plan**: a Markdown file describing one piece of work (`<id>_<slug>.md`)
- **status**: where the plan is in its lifecycle (see below)
- **wave**: a batch of plans being worked on in parallel
- **worktree**: an isolated working directory for one plan (`.worktrees/<id>/`)
- **orchestrator**: the session coordinating all the others; runs in the main project directory
- **main session**: a session launched by the orchestrator to work one plan in its own worktree

## Plan status lifecycle

```
draft → ready → in_progress → done | cancelled | blocked
```

| Status | Meaning |
|---|---|
| `draft` | Just created, not ready for execution |
| `ready` | Worktree-ready, awaiting session launch |
| `in_progress` | Session active, working the plan |
| `done` | Plan complete |
| `cancelled` | Plan no longer relevant (reason required) |
| `blocked` | Stuck on external dependency (reason required) |

## Plan MD structure

Each plan MD must include:

```markdown
# {ID}_{slug} — {Title}

## Status
{draft|ready|in_progress|done|cancelled|blocked}

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

## Related
Links to other plans, memory entries, docs.

## Execution log
Append-only. Each entry: date + what happened.
```

The execution log is **mandatory**. It's the audit trail.

## Operating rules for main sessions

A main session:

- **Owns its plan** from start to terminal state (`done`/`cancelled`/`blocked`)
- **May talk to the user directly** for clarifications, decisions, etc.
- **May commit, push, and open PRs** as appropriate (see PR/push policy below)
- **Updates its own plan MD** (status + execution log)
- **Updates its own row in `_progress.md`** (in the worktree copy)

A main session must NOT:

- **Edit other plans' worktrees**
- **Push to `main` directly** (PR or local merge by user is the path)
- **Touch `.gitignore` to remove `.worktrees/`** (we want worktrees ignored)
- **Make scope decisions outside its plan** (escalate to user or note as "out of scope")

## Dependency handling

If your plan depends on another plan that's not yet done:

1. Check if the other plan is in a `plan/<id>` branch — you can fetch and reference it
2. If you're truly blocked, set status to `blocked` and record `blocked on plan-<id>` in the execution log
3. The orchestrator will reassign or wait

## PR/push policy

| Case | push | PR |
|---|---|---|
| New feature / large implementation | **required** | **recommended** |
| New plan MD / docs only (chore) | recommended | not needed |
| Implicit done verdict (no code change) | recommended | not needed |
| Bug fix | **required** | **recommended** |
| Tests added alone | **required** | **not needed** (tests get their own audit phase) |
| Security / fallback removal | **required** | **required** |
| INDEX done verdict | recommended | not needed |
| Cancelled verdict | recommended | not needed |

Commit messages should include the plan ID, e.g. `feat(plan-123): add user search`.

## Worktree conventions

```
Path:       .worktrees/<plan_id>/
Branch:     plan/<plan_id>
Base:       origin/main (or your project's main equivalent)
```

The `.worktrees/` directory is in `.gitignore`. Do not commit it.

## Reporting completion

When a plan reaches a terminal state, the session should write a **completion summary** for the user to paste to the orchestrator. Recommended format:

```
plan {ID} → {done|cancelled|blocked}

What changed:
- file1.py (+50/-10)
- file2.py (new, 200 lines)
- ...

Tests:
- test_X 15/15 PASS
- regression: existing 200 tests still pass

PR:
- PR #123 created (or "not created — chore")

Push:
- plan/{ID} pushed to origin (or "local commit only — reason")

Residual issues (out of scope for this plan):
- [...]

Notes for orchestrator:
- [anything cross-cutting]
```

The user pastes this to the orchestrator; the orchestrator updates `_progress.md` and acknowledges.

## When to call it `cancelled` instead of `done`

You may judge `cancelled` when:

- Plan's premise no longer holds (architecture shift, requirements changed)
- Plan is duplicated by another plan with equivalent scope
- Implementation cost is much higher than expected and value is unclear (escalate first, but cancellation is a valid outcome)

Always include the cancellation reason in the execution log.

## When to call it `blocked`

You may judge `blocked` when:

- Waiting on external party (vendor approval, partner integration)
- Waiting on another plan that's been assigned to a different session
- Tool / environment issue you can't resolve

Set status `blocked`, record what's blocking, and stop. Don't loop.

## Notes about `_progress.md`

- The master `_progress.md` lives in the orchestrator's working directory only
- Each worktree gets a **read-only snapshot** at launch
- You may edit the snapshot in your worktree (it helps your own bookkeeping) but the orchestrator will re-apply your change to the master
- **Do not** try to merge `_progress.md` from branches — it's operational state, not source code

## Common questions

**Q: Should I create a PR?**
See the PR/push table above. When in doubt, push without PR; the orchestrator can decide later.

**Q: I found a bug not in my plan's scope. What do I do?**
Document it (in execution log + as a new plan suggestion to the orchestrator). Don't fix it unless it's blocking your own plan.

**Q: My plan turned out to be impossible / wrong / done already. What do I do?**
Set status appropriately (`cancelled` or `done (implicit)`), write reasoning, and stop. Don't fight the plan.

**Q: I need help from another session.**
You can't talk to other sessions directly. Either ask the user, or annotate your plan as `blocked on plan-X` and stop.

**Q: I'm out of context and the plan isn't done.**
Save your progress in the plan MD's execution log, push your branch, set status back to `ready` with notes about where you stopped. The orchestrator can spawn a follow-up session.
