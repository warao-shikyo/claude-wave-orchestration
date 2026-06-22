# Pattern: Session monitoring

In the original engagement we had **no way to see live session state** (see [ANTI-PATTERNS.md #5](../ANTI-PATTERNS.md#5-we-tracked-sessions-by-completion-summary-only)). The orchestrator only knew a session existed; whether it was working, waiting for user input, or silently dead was invisible until the user pasted a summary. This worked at ≤10 sessions in flight but is the first thing that breaks as you scale.

This pattern adds **lightweight liveness tracking** without introducing a daemon or polling loop.

## The problem, concretely

- A session gets stuck waiting for user input. The orchestrator doesn't know and starts planning the next Wave as if this one finished.
- A session crashes (context exhaustion, terminal closed). No summary ever arrives. The row sits at `in_progress` forever.
- The user can't tell, at a glance, which of 10 open conversations still need their attention.

## Two complementary mechanisms

You don't need both. Start with B (zero session-side cost); add A if you want a single dashboard view.

### A. `last_activity` heartbeat in `_progress.md`

Add a `last_activity` column to the dashboard. Each session stamps it at meaningful checkpoints (start, after each commit, when it asks the user a question, at completion).

```markdown
| ID | Title | wave | status | launched_at | last_activity | branch | notes |
|---|---|---|---|---|---|---|---|
| api-003 | Test recovery | 4 | in_progress | 14:02 | 14:37 | plan/api-003 | running suite |
```

Rule of thumb for the orchestrator (or user) reading it:

- `last_activity` within ~15 min → session is alive and working
- `last_activity` 15–45 min stale **and** status still `in_progress` → probably waiting on the user; go check that conversation
- `last_activity` 45+ min stale → likely dead; consider re-launching from the plan MD's execution log

The session updates its **own row in its worktree snapshot**, exactly like it already does for status. The orchestrator re-applies it to the master only when it processes that session's summary — so for *live* monitoring, the user reads the worktree snapshots, or uses mechanism B.

### B. `git log` spot-check (zero session-side cost)

The branches don't lie. A session that's working is committing; a session that hasn't committed in an hour has either stalled or is mid-conversation.

```bash
# Which plan branches have shipped commits recently?
git log --all --oneline --since='1 hour ago' | grep 'plan-'

# Last commit time per active plan branch
git for-each-ref --sort=-committerdate \
  --format='%(committerdate:relative)  %(refname:short)' \
  refs/heads/plan/

# Worktrees that exist but show no recent commits → candidates to check on
ls .worktrees/
```

This requires **nothing from the sessions** and survives crashes (the commits are real even if the terminal died). The downside: it only sees committed work, so a session doing a long uncommitted investigation looks idle. That's acceptable — pair it with the heartbeat (A) if it matters.

**Orchestrator context cost**: running `git log` inflates the orchestrator's context (see [METHODOLOGY.md §12](../METHODOLOGY.md#12-context-economy-orchestrator-side)). Prefer to have the **user** run the spot-check and only escalate findings to the orchestrator ("plan 415 has no commits in 50 min — should I re-launch?").

## Detecting "Wave done" reliably

A Wave is done when every row is `done`/`cancelled`/`blocked`. Mechanism B catches the failure mode where a session closes without emitting a summary:

```bash
# Sessions still expected to report:
#   rows at in_progress in _progress.md
# vs branches that look finished:
git log --all --oneline --since='today' | grep 'plan-'

# Plans that renamed themselves to _done (the explicit completion signal):
git log --all --diff-filter=A --since='today' --name-only --pretty=format: | grep '_done\.md$'
```

A completed plan leaves two detectable traces: a `<id>-<slug>_done.md` file appearing in its branch, and/or a `chore(plan-<id>): mark done` commit. If a row is `in_progress` but its branch shows either of those, the summary was probably just lost in the shuffle — ask the user to re-paste, or read the plan MD's execution log directly.

## Session-side rule (goes in INSTRUCTIONS.md / starter prompt)

> Stamp `last_activity` (HH:MM) on your row whenever you: start, finish a commit, ask the user a blocking question, or reach a terminal state. This is cheap bookkeeping, not a status change.

## What this pattern deliberately does NOT do

- **No polling daemon.** The orchestrator still doesn't poll (that burns context and the model's attention). Liveness is checked *on demand* — when the user wonders "is Wave 4 actually done?".
- **No automatic re-launch.** A stale session is surfaced, not auto-restarted. Re-launch is a user decision (the plan MD's execution log tells you where it stopped).
- **No cross-process messaging.** Sessions remain independent. This pattern only reads shared artifacts (`_progress.md`, git history).

## When to scale past this

If you routinely run 20+ sessions, or run them unattended, the heartbeat-in-a-Markdown-table approach gets unwieldy. At that point consider instrumenting the launcher to log PIDs (see [`scripts/launch_claude.py`](../scripts/launch_claude.py) launch log) and writing a small status script that joins the launch log with `git for-each-ref`. That's out of scope for the file-based method described here.

## TL;DR

1. Add a `last_activity` column; sessions stamp it at checkpoints.
2. For crash-proof truth, `git log --all --since=1h | grep plan-` — branches don't lie.
3. Let the **user** run spot-checks; escalate only findings to the orchestrator (context economy).
4. Surface stale sessions; don't auto-restart.
