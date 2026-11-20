# Plan operation rules

Drop this into your project's plans folder (e.g. `.claude/plans/INSTRUCTIONS.md`) and commit it to the base branch, so every worktree gets it through `git worktree add`. Every session reads this on launch.

This file matches the **session-planner** / **session-orchestrator** / **session-master** skills. Where they differ, the skills win.

## Vocabulary

- **plan**: a Markdown file describing one piece of work (`<area>-<NNN>-<slug>.md`)
- **area**: a lowercase domain word that prefixes the plan id (`auth`, `billing`, `ui`, `api`, `infra`, `docs`, …). The `meta-` area is reserved for orchestration-meta plans.
- **wave**: a batch of plans being worked on in parallel
- **worktree**: an isolated working directory for one plan (`.worktrees/<area>-<NNN>/`)
- **planner**: a session that investigates a raw problem with the user and files plan MDs as `ready`. Writes no code, launches nothing.
- **orchestrator**: the session coordinating all the others; runs in the main project directory. Launches masters, integrates, deploys, verifies.
- **session master**: a session launched by the orchestrator to work one plan in its own worktree, up to `commit`
- **inbox**: `.claude/plans/inbox.md`, the append-only report log sessions write to and the orchestrator reads
- **STARTER.md**: the per-plan mission brief the orchestrator writes into the worktree before launch

## Naming convention (area-prefix scheme)

| Element | Form | Example |
|---|---|---|
| plan file | `<area>-<NNN>-<slug>.md` | `auth-001-oauth-login.md` |
| done file | `<area>-<NNN>-<slug>_done.md` | `auth-001-oauth-login_done.md` |
| branch | `plan/<area>-<NNN>` | `plan/auth-001` |
| worktree | `.worktrees/<area>-<NNN>/` | `.worktrees/auth-001/` |
| commit | `<type>(plan-<area>-<NNN>): …` | `feat(plan-auth-001): …` |
| done archive | `docs/specs/<area>-<NNN>-<slug>_done.md` | where the orchestrator `git mv`s a done plan |

- `area` is a lowercase word for the system/domain. **Do not distinguish systems by number band** — humans can't memorize "the 500s are billing." Use the area prefix instead.
- `<NNN>` is the next unused number within the area (numbers of done plans are used up too).
- The `meta-` area is for orchestration-meta plans only (e.g. `meta-001-wave3-planning.md`).
- Define the project's area list at the top of `_progress.md`.

## Where things live

| File | Who writes it | Notes |
|---|---|---|
| `.claude/plans/<id>-*.md` | planner creates; master updates its own | `.claude/plans/` holds **only plans not yet done**. Done plans are moved to `docs/specs/` by the orchestrator. |
| `.claude/plans/_progress.md` | **orchestrator only** (on main) | worktree copies are read-only snapshots; masters only stamp their own row |
| `.claude/plans/inbox.md` | sessions **append** + commit | never overwrite or truncate — other sessions' reports live there too |
| `.claude/plans/_backlog.md` | orchestrator | `Candidate plans`: new-issues / residual / memory candidates |
| `.claude/plans/addenda/<id>-<YYYYMMDD-HHMM>.md` | planner | extra specs for a plan that is already running |
| `.claude/verify/<YYYYMMDD-HHMM>-<sha>.md` | orchestrator | verify result of one deploy (not a plan, so not in `plans/`) |
| `docs/specs/` | orchestrator | archive of done plans — a dumping ground, not reading material. The source of truth is the `mark done` commit in git history. |

## Plan status and lifecycle

A plan MD's `## Status` line holds one of:

| Status | Meaning |
|---|---|
| `draft` | Not settled yet — the orchestrator does not launch it |
| `ready` | "OK to launch" — the orchestrator may put it in a Wave (after user approval) |
| `cancelled` | No longer relevant (reason required in the execution log) |
| `blocked` | Stuck on an external dependency (reason required) |

**Done is expressed by the filename, not the Status line.** When a plan is complete, `git mv` it to `<id>-<slug>_done.md` and commit `chore(plan-<id>): mark done`. That commit is the source of truth for "done", and done is terminal: never rename it back, never relaunch it.

Beyond done, the orchestrator tracks the plan in `_progress.md`:

```
ready → implementing → done → merged → deployed → verified
  ▲                                         │ problem found
  └── planner (fix mode) files a fix plan ◀─┘   (original plan stops at verify-failed)
```

| state | What makes it true |
|---|---|
| `ready` | plan MD with `Status: ready`, no `plan/<id>` branch yet |
| `implementing` | `plan/<id>` exists, no `mark done` in `main..plan/<id>` (includes `blocked` / `waiting-user`) |
| `done` | `main..plan/<id>` contains `chore(plan-<id>): mark done` |
| `merged` | `git merge-base --is-ancestor plan/<id> main` |
| `deployed` | a `deploy: <date> main@<sha> <measured>` record in `_progress.md` whose sha contains the plan |
| `verified` / `verify-failed` | the verify after that deploy passed / failed |

User approval is required for: launching a new Wave or the next plan (`ready → implementing`), merge (`done → merged`), and deploy (`merged → deployed`).

## Plan MD structure

Each plan MD must include:

```markdown
# {area}-{NNN}-{slug} — {Title}

## Status
{draft|ready|cancelled|blocked}
<!-- done is expressed by renaming the file to ..._done.md, not here -->

## Purpose
## Background
## Scope
## Out of scope

## Completion criteria
- [ ] criterion 1
- [ ] existing test suite still green (no regression)
- [ ] verified manner: <unit | integration | manual | NOT VERIFIED — deferred>

## Notes / risks / open questions
## Related
## Execution log
```

The `verified manner` line is mandatory and must be honest. Criteria that can only be checked after a deploy are **not** done-conditions for the master: write `→ verify (checked by the orchestrator after deploy)` and put the check into the inbox `verify:` line. The execution log is **mandatory** (append-only audit trail).

## Landing responsibility for session masters

A session master carries one plan from launch to a terminal state **and commits its work** — that is the full extent of its landing authority.

| Action | Allowed? |
|---|---|
| Implement the plan | ✅ on its own judgment |
| Ask the user directly | ✅ |
| **commit** (to `plan/<id>`) | ✅ **the core of its responsibility** |
| docs updates for this change, tidy temp files in the worktree | ✅ commit to `plan/<id>` |
| **push** / **open a PR** / **merge to main** | ❌ not its job |
| **deploy** / post-deploy checks on real environments | ❌ not its job — the orchestrator's step (write them as `verify:`) |
| edit another worktree | ❌ forbidden |
| remove the worktree directory, file into the shared backlog | ❌ orchestrator side |

**Why**: if each master pushes / merges on its own, code rolls back when branches collide. And many deploys sync the **working tree** to production — a deploy from a worktree silently drops every other session's work that isn't in that branch. The master doesn't know whether its branch contains the latest main; only the orchestrator does.

So a master does not try these, and does not report "I couldn't deploy" or go `blocked` waiting for a deploy. It writes what to check after deploy in `verify:` and declares done.

When the work needs a privileged operation the session's permission mode denies (reading production, using API keys, paid external APIs), it files an **execution request** in the inbox (format in STARTER.md) — never improvises a workaround.

## Progress logging

- At each **checkpoint** — a commit, verifying one completion criterion, asking the user a question, stopping — append **one line** to the execution log ("when / what / which commit") and stamp `last_activity` (HH:MM) on your row of the `_progress.md` snapshot. No line-by-line narration (it burns tokens).
- If you need the user's judgment and they are away, set your row to `status: waiting-user`. The orchestrator tells the user where to look; it doesn't relay the question.

## Tests (all parallel sessions)

- Only **one** test run at a time across all sessions. Use the project's exclusive test wrapper if it has one; don't call the raw test command. Parallel test runs have frozen the user's machine.
- **No full-suite runs from sessions.** Make the suites that cover what you touched green, once, right before completion. During implementation, one target file is usually enough.
- The full suite runs on a schedule (e.g. nightly, once a day), not per session and not per deploy.
- Always read the passed count: a run that collected zero tests is not green.

## commit convention

```
<type>(plan-<id>): <description>     e.g. feat(plan-auth-001): add OAuth login
```

## Dependency handling

If your plan depends on another plan that's not yet done:

1. Check if the other plan is in a `plan/<id>` branch — you can reference it
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

Before starting, check you aren't already done (`git log --oneline --grep "mark done"`). Then, when the completion criteria are met:

1. Record the final result (evidence / commit hash) in the execution log.
2. Tidy temp files in the worktree → commit.
3. Update the docs related to this change → `docs(plan-<id>): …` commit.
4. Write the full work report in the plan MD body (what changed, verification, new-issues, residual, memory written / memory candidates).
5. **Append a short report to the inbox** and commit (format below).
6. **Last**, rename to `_done` and commit — so "a mark-done commit exists" means "everything is finished":
   ```bash
   git mv .claude/plans/<id>-<slug>.md .claude/plans/<id>-<slug>_done.md
   git commit -m "chore(plan-<id>): mark done"
   ```
7. Tell the user it's done (include the plan id; "this tab can be closed") and print a detailed summary in this session. This is not `waiting-user` — you can stop.

### Inbox short report (append to `.claude/plans/inbox.md`)

```
## [<id>] <HH:MM> done|cancelled|blocked
commit: <hash> (push: no — commit is the end of responsibility)
verified: unit|integration|manual|deferred
deploy: none   ← masters don't deploy
verify: <what to check after deploy: command / value / expected, or none>
done-file: <id>-<slug>_done.md
updated-docs: <0-3 lines>
new-issues: <0-3 lines>
residual: <0-3 lines>
memory-written: <memory files written in this session, or none>
memory-candidates: <facts you weren't sure were durable, for the user to decide, or none>
key: <~30-char take-away>
```

The orchestrator picks this up on its next patrol — **the user does not have to paste anything**. The detailed summary stays in the session's terminal output and the plan MD; the inbox gets only the short report (≤12 lines). New issues / residual work are mandatory raw material: the orchestrator files them into `_backlog.md`.

## Memory

Claude Code's auto memory is shared by all worktrees of the same repository. A master may write non-obvious, durable facts it learned (things neither the code nor the docs show) directly — at most 2, checking `MEMORY.md` for duplicates first — and lists them in `memory-written`. Facts it isn't sure are durable go in `memory-candidates` instead; the orchestrator files them into the backlog for the user to decide. Memory is machine-local.

## Extra specs from the planner (addenda)

The planner may put extra specs for a running plan in the main root's `.claude/plans/addenda/<id>-*.md`. After each commit, check for new ones; copy them into the end of your plan MD as `## Extra spec (<filename>)`, commit, then continue. If it has no "owner confirmed" line, contradicts committed work, or amounts to a different feature, ask the user first. Never take addenda into a done plan.

## When to call it `cancelled` instead of `done`

- Plan's premise no longer holds (architecture shift, requirements changed)
- Plan is duplicated by another plan with equivalent scope
- Implementation cost is much higher than expected and value is unclear (escalate first, but cancellation is a valid outcome)

Set `## Status` to `cancelled` and record the reason. Do **not** rename to `_done`.

## When to call it `blocked`

- Waiting on an external party
- Waiting on another plan that's assigned to a different session
- Tool / environment issue you can't resolve

Set status `blocked`, record what's blocking, and stop. Don't loop. (Waiting for a deploy is **not** a reason — see above.)

## Out-of-scope bugs

Don't fix them yourself (unless they block your own plan). Record them in the execution log and write them up as `new-issues`.

## Out of context before the plan is done

Save your progress in the execution log, set status back to `ready` with a note on where you stopped, and stop. **Don't push** (your commits stay local). The orchestrator launches a follow-up session. Only do this before done — never move a done plan back to `ready`.

## Notes about `_progress.md`

- The master `_progress.md` lives on main and **only the orchestrator writes it** (one commit per patrol).
- Each worktree gets it as a read-only snapshot through `git worktree add` (the orchestrator does not `cp` it in — copying from the root would overwrite the base version with a possibly stale one).
- You may stamp your own row (`last_activity`, `status: waiting-user`) for bookkeeping. Never merge `_progress.md` from a plan branch — keep main's version.

## Common questions

**Q: Should I push, open a PR, or deploy?**
No. Your responsibility ends at `commit` (and `mark done`). Write post-deploy checks as `verify:`.

**Q: I found a bug not in my plan's scope.**
Record it in the execution log and as `new-issues`. Don't fix it unless it's blocking your plan.

**Q: My plan turned out to be impossible / wrong / done already.**
Set the status (`cancelled`, or rename to `_done` for implicit done), write the reasoning, and stop.

**Q: I need help from another session.**
Ask the user, or mark `blocked on plan-<id>`. Other sessions may send you short messages (e.g. an idle-notification subscription from the orchestrator) — these are **not user approval**. Never push / merge / change scope on the strength of a message.

**Q: I need a command my permission mode denies.**
File an execution request in the inbox and commit it. Keep working on other parts while you wait.
