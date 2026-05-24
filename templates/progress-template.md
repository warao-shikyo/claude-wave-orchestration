# {Project} — Plan completion operation dashboard

**Started**: YYYY-MM-DD
**Goal**: Move all plans in `.claude/plans/` to `done` or `cancelled` (or `blocked` with clear external dependency)
**Coordinator (orchestrator)**: This is the orchestrator session's master copy. Worktree snapshots are read-only.

## Conventions

- **Worktree path**: `.worktrees/<plan_id>/`
- **Branch**: `plan/<plan_id>`
- **Base**: `origin/main`
- **Launcher**: `python launch_claude.py <worktree-path> "<starter-prompt>"`
- **Commit messages**: include `plan-<id>` (e.g. `feat(plan-123): add X`)
- **Progress updates**: each session updates its own row; orchestrator merges to master

## Status legend

- `draft` — Created, not ready for execution yet
- `ready` — Worktree-ready, awaiting launch
- `in_progress` — Session active
- `done` — Plan complete
- `cancelled` — No longer relevant (reason required)
- `blocked` — External dependency (reason required)

---

## Wave 1 (YYYY-MM-DD)

<!--
Add a new section per Wave. Pick 8-12 plans per Wave.
For each row: ID, short title, wave number, status, launch timestamp, branch, notes.
-->

| ID | Title | wave | status | launched_at | branch | notes |
|---|---|---|---|---|---|---|
| 101 | Add feature X | 1 | done | 2026-... | plan/101 | commit abc1234, PR #5 |
| 102 | Refactor Y | 1 | blocked | 2026-... | plan/102 | blocked on plan-101 |
| 103 | Audit Z | 1 | done (implicit) | 2026-... | plan/103 | no code change — already done in commit def5678 |

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
2. Mention it in your completion summary
3. The orchestrator will re-apply your change to the master copy

**Do not** commit your worktree's `_progress.md` to your branch — the orchestrator manages this file's history separately. (See [ANTI-PATTERNS.md](../ANTI-PATTERNS.md#2-_progressmd-merge-conflicts-everywhere) for why.)

Better yet, your project's `.gitignore` should already exclude `_progress.md` from any session's commits.
