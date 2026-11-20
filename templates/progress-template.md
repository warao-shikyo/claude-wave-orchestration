# {Project} — Plan completion operation dashboard

**Started**: YYYY-MM-DD
**Goal**: Move all plans in `.claude/plans/` to `done` or `cancelled` (or `blocked` with clear external dependency)
**Coordinator (orchestrator)**: This file lives on main and **only the orchestrator writes it** (one commit per patrol). Worktrees get it as a read-only snapshot through `git worktree add`.

## Conventions

- **Plan file**: `<area>-<NNN>-<slug>.md` (e.g. `auth-001-oauth-login.md`); **done is expressed by renaming the file to `<area>-<NNN>-<slug>_done.md`**, not by flipping the Status field
- **Worktree path**: `.worktrees/<area>-<NNN>/`
- **Branch**: `plan/<area>-<NNN>`
- **Base**: `integration/latest-known-good` (preferred) — fall back to `origin/main` only on Wave 1, before any integration branch exists. Basing on stale `origin/main` is the #1 anti-pattern; see [between-Wave integration](../patterns/main-merge-strategy.md#between-wave-integration-during-the-operation).
- **Launcher**: `MSYS_NO_PATHCONV=1 python launch_claude.py "$(pwd -W)/.worktrees/<id>" --role master --plan-id <id> --task "<plan title>" "/session-master <id>（.claude/plans/STARTER.md を読んで開始）"`
- **Commit messages**: include `plan-<area>-<NNN>` (e.g. `feat(plan-auth-001): add OAuth login`)
- **Landing model**: masters commit only. Merge to main and deploy are the orchestrator's steps, each with user approval; push / PR are the user's call. Masters never deploy.
- **Reports**: masters append to `.claude/plans/inbox.md` and commit; the orchestrator ingests the inbox on each patrol (the user doesn't paste summaries)
- **Backlog**: `.claude/plans/_backlog.md` (`Candidate plans`)
- **Done archive**: done plans are `git mv`ed to `docs/specs/` — `.claude/plans/` holds only plans not yet done
- **Launch log**: `~/.claude/wave-launch-log.jsonl` (set by the launcher) — reconcile per-session cost here

## Area registry & idle counter

<!--
`area` is a lowercase domain word (auth, billing, ui, api, infra, docs, ...) that
prefixes every plan id. Do NOT distinguish systems by number ranges — humans can't
memorize those. `meta-` is reserved for orchestration / meta plans.
`wake_mode` is decided once after the first launches: `notify` (masters' idle
notifications + a 60-min ScheduleWakeup fallback) or `poll` (ScheduleWakeup every 20-30 min).
`idle_cycles` counts consecutive fallback/poll wakes with no new done and no new
`plan-` commits (notification wakes count as change). At 3 the orchestrator stops
sleeping and waits for the user.
-->

- **Areas in use**: `auth`, `billing`, `ui`, `api`, `infra`, `docs`, `meta` (edit for your project)
- **wake_mode**: notify | poll
- **idle_cycles**: 0
- **concurrent masters**: 3-6 (tests and CPU are shared; tune to the machine)

## Deployment baseline (capture before Wave 1)

<!--
Record what is ACTUALLY LIVE in production at operation start. Sessions must
distinguish "code present in a branch" from "running in production". See
ANTI-PATTERNS.md #11 and METHODOLOGY.md §0.
-->

- **Production commit/tag**: `<hash or tag>` (what's live right now)
- **Captured on**: YYYY-MM-DD
- **Environments**: prod = `<ref>`, staging = `<ref>`
- Masters always report `deploy: none` — only the orchestrator deploys. Each deploy is recorded below as
  `deploy: <date> main@<sha> <measured value>` and followed by a verify: `verify: <date> main@<sha> pass|fail .claude/verify/<file>`

### Deploy / verify records

- deploy: YYYY-MM-DD HH:MM main@<sha> <revision / content hash measured>
- verify: YYYY-MM-DD HH:MM main@<sha> pass .claude/verify/YYYYMMDD-HHMM-<sha>.md

## State legend (`state:` per plan — a note; the facts on the right are the source of truth)

- `ready` — plan MD is `Status: ready`, no `plan/<id>` branch yet
- `implementing` — branch exists, no `mark done` in `main..plan/<id>` (includes `blocked` / `waiting-user`)
- `done` — `chore(plan-<id>): mark done` in `main..plan/<id>` (terminal for the master)
- `merged` — `git merge-base --is-ancestor plan/<id> main`
- `deployed` — a deploy record above whose sha contains the plan
- `verified` / `verify-failed` — the verify after that deploy passed / failed (`verify-failed → <fix-plan-id>`)
- `cancelled` / `blocked` — plan MD Status with a reason (no rename)
- extra marks: `postprocessed` (archive/stop/worktree removal done), `asked: <date>` (approval requested), `run-request: <date> done|refused`

---

## Wave 1 (YYYY-MM-DD)

<!--
Add a new section per Wave. Pick 8-12 plans per Wave.
For each row: ID, short title, wave number, status, launch timestamp,
last_activity (session-stamped heartbeat — see session-monitoring.md), branch, notes.
-->

| ID | Title | wave | state | launched_at | last_activity | branch | notes |
|---|---|---|---|---|---|---|---|
| auth-001 | Add OAuth login | 1 | verified | 14:02 | 14:51 | plan/auth-001 | commit abc1234, postprocessed, verify: login smoke test |
| billing-002 | Refactor invoicing | 1 | implementing (blocked) | 14:02 | 14:20 | plan/billing-002 | blocked on plan-auth-001 |
| api-003 | Audit search endpoint | 1 | done (implicit) | 14:03 | 14:18 | plan/api-003 | no code change — already done in commit def5678 |

---

## Wave 2 (YYYY-MM-DD)

(...)

---

## Candidate plans for future Waves

<!--
Plans not yet in a Wave. The backlog of record is `.claude/plans/_backlog.md`
(new-issues / residual / "memory candidate (needs user decision)" from the inbox go there);
keep only a pointer or a short list here.
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

## Instructions to sessions about this file

You are a session master reading a snapshot of this file:

1. Find your row. You may stamp `last_activity` (HH:MM) at checkpoints — a commit, verifying a criterion, asking the user, stopping — and set `status: waiting-user` when you need the user and they're away. That's all you write here.
2. Report through the inbox (`.claude/plans/inbox.md`, append + commit) — the orchestrator updates this file from there.
3. When the plan is complete, rename the plan file to `..._done.md` (last step, `chore(plan-<id>): mark done`). `cancelled` / `blocked` stay as a Status with a reason — no rename.
4. Your landing authority ends at `commit`: `push: no`, `deploy: none`. Post-deploy checks go into the inbox `verify:` line.

**Never** merge this file from a plan branch — keep main's version (see [ANTI-PATTERNS.md](../ANTI-PATTERNS.md#2-_progressmd-merge-conflicts-everywhere)).
