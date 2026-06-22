# {Project} — Plan completion operation dashboard

**Started**: YYYY-MM-DD
**Goal**: Move all plans in `.claude/plans/` to `done` or `cancelled` (or `blocked` with clear external dependency)
**Coordinator (orchestrator)**: This is the orchestrator session's master copy. Worktree snapshots are read-only.

## Conventions

- **Plan file**: `<area>-<NNN>-<slug>.md` (e.g. `auth-001-oauth-login.md`); **done is expressed by renaming the file to `<area>-<NNN>-<slug>_done.md`**, not by flipping the Status field
- **Worktree path**: `.worktrees/<area>-<NNN>/`
- **Branch**: `plan/<area>-<NNN>`
- **Base**: `integration/latest-known-good` (preferred) — fall back to `origin/main` only on Wave 1, before any integration branch exists. Basing on stale `origin/main` is the #1 anti-pattern; see [between-Wave integration](../patterns/main-merge-strategy.md#between-wave-integration-during-the-operation).
- **Launcher**: `python launch_claude.py <worktree-path> "<starter-prompt>"`
- **Commit messages**: include `plan-<area>-<NNN>` (e.g. `feat(plan-auth-001): add OAuth login`)
- **Landing model**: sessions commit only — push / PR / merge to main are the user's call (deploy from the worktree for verification only)
- **Progress updates**: each session updates its own row; orchestrator merges to master
- **Launch log**: `~/.claude/wave-launch-log.jsonl` (set by the launcher) — reconcile per-session cost here

## Area registry & idle counter

<!--
`area` is a lowercase domain word (auth, billing, ui, api, infra, docs, ...) that
prefixes every plan id. Do NOT distinguish systems by number ranges — humans can't
memorize those. `meta-` is reserved for orchestration / meta plans.
`idle_cycles` is the orchestrator's consecutive-no-change counter for the 20-min
sleep loop: it sleeps (ScheduleWakeup, 1200s) after launching a wave and re-checks;
after 3 cycles (~60 min) with no new `_done` files and no new `plan-` commits, it
stops sleeping and waits for the user.
-->

- **Areas in use**: `auth`, `billing`, `ui`, `api`, `infra`, `docs`, `meta` (edit for your project)
- **idle_cycles**: 0

## Deployment baseline (capture before Wave 1)

<!--
Record what is ACTUALLY LIVE in production at operation start. Sessions must
distinguish "code present in a branch" from "running in production". See
ANTI-PATTERNS.md #11 and METHODOLOGY.md §0.
-->

- **Production commit/tag**: `<hash or tag>` (what's live right now)
- **Captured on**: YYYY-MM-DD
- **Environments**: prod = `<ref>`, staging = `<ref>`
- Sessions report deploy status as one of: `none` / `verified-on-deploy` / `live` (sessions commit only; merge to main is the user's call, so there is no `merged-not-deployed` session state)

## Status legend

- `draft` — Created, not ready for execution yet
- `ready` — Worktree-ready, awaiting launch
- `in_progress` — Session active
- `done` — Plan complete (the session renames the plan file to `..._done.md` to signal this)
- `cancelled` — No longer relevant (reason required; stays as a Status, file is NOT renamed)
- `blocked` — External dependency (reason required; stays as a Status, file is NOT renamed)

---

## Wave 1 (YYYY-MM-DD)

<!--
Add a new section per Wave. Pick 8-12 plans per Wave.
For each row: ID, short title, wave number, status, launch timestamp,
last_activity (session-stamped heartbeat — see session-monitoring.md), branch, notes.
-->

| ID | Title | wave | status | launched_at | last_activity | branch | notes |
|---|---|---|---|---|---|---|---|
| auth-001 | Add OAuth login | 1 | done | 14:02 | 14:51 | plan/auth-001 | commit abc1234, push: no, deploy: none, done-file: auth-001-oauth-login_done.md |
| billing-002 | Refactor invoicing | 1 | blocked | 14:02 | 14:20 | plan/billing-002 | blocked on plan-auth-001 |
| api-003 | Audit search endpoint | 1 | done (implicit) | 14:03 | 14:18 | plan/api-003 | no code change — already done in commit def5678 |

---

## Wave 2 (YYYY-MM-DD)

(...)

---

## Candidate plans for future Waves

<!--
Plans not yet in a Wave but tracked for future inclusion.
Group by area / type.
-->

### Domain A

- 201, 202, 203

### Domain B

- 301, 302

### Maybe-cancel candidates

- ...

---

## Cross-cutting findings

<!--
Things discovered during Waves that affect multiple plans.
Use this section to keep the orchestrator (and the user) informed.

Examples:
- "Session for plan 415 discovered a regression in the test suite that affects plans 416-418."
- "Plan 761 turned out to have a different scope than intended; created plan 761b for the actual intent."
- "All sessions in Wave 5 reported the same warning — file an infrastructure ticket?"
-->

- ...

---

## Special cases (long-running / external dependencies)

<!-- Items not in normal Wave flow because of external dependencies. -->

| ID | Description | Why special |
|---|---|---|
| 999 | Awaits vendor approval | Vendor processing takes 1-2 weeks |

---

## Operation log

<!--
Free-form log of the operation. Append-only.

Examples:
YYYY-MM-DD
- HH:MM Wave 1 launched: 101, 102, 103, ...
- HH:MM 103 reported done
- HH:MM 102 reported blocked

YYYY-MM-DD
- 09:00 Wave 1 fully landed (8 done, 1 cancelled, 1 blocked)
- 09:30 Wave 2 planning: ...
-->

### YYYY-MM-DD

- ...

---

## Instructions to sessions about updating this file

When you're a main session and want to update your own row:

1. Edit your row in this file (in your worktree's copy)
2. **Stamp `last_activity` (HH:MM)** whenever you start, finish a commit, ask the user a blocking question, or reach a terminal state. This is cheap bookkeeping for liveness monitoring — not a status change. See [session-monitoring.md](../patterns/session-monitoring.md).
3. When the plan is complete, **rename the plan file to `..._done.md`** (the orchestrator detects done by that filename) and note `done-file:` in your row. `cancelled` / `blocked` stay as a Status with a reason — no rename.
4. Your landing authority ends at `commit`: record `push: no` and your deploy status in `notes` as `none` / `verified-on-deploy` / `live`. push / PR / merge to main are the user's call.
5. Put any new issues / residual work in your completion summary — the orchestrator files them into the backlog.
6. Mention the change in your completion summary; the orchestrator re-applies your change to the master copy.

**Do not** commit your worktree's `_progress.md` to your branch — the orchestrator manages this file's history separately. (See [ANTI-PATTERNS.md](../ANTI-PATTERNS.md#2-_progressmd-merge-conflicts-everywhere) for why.)

Better yet, your project's `.gitignore` should already exclude `_progress.md` from any session's commits.
