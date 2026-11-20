# Pattern: Session monitoring

In the original engagement we had **no way to see live session state** (see [ANTI-PATTERNS.md #5](../ANTI-PATTERNS.md#5-we-tracked-sessions-by-completion-summary-only)). The orchestrator only knew a session existed; whether it was working, waiting for user input, or silently dead was invisible until the user pasted a summary.

This pattern combines four cheap signals so the orchestrator wakes **only when something changed**, and the user knows **which tab needs them**.

## The problem, concretely

- A session gets stuck waiting for user input. The orchestrator doesn't know and plans the next Wave as if this one finished.
- A session crashes (context exhaustion, terminal closed). No report ever arrives. The row sits at `implementing` forever.
- The user can't tell which of several open conversations need their attention.
- Polling every few minutes burns the orchestrator's context and usage limits on "nothing changed".

## 1. Wake on idle notifications (the orchestrator's trigger)

Claude Code's cross-session messaging lets the orchestrator subscribe to a master's **idle** event: `SendMessage` with `notify_when_idle` and no body. When the master's turn ends, the orchestrator gets a one-line notification and wakes. Subscribing costs the master nothing.

- Decide once after the first launches, and record `wake_mode: notify|poll` in `_progress.md`. Use **notify** only if all hold: the `ListAgents` / `SendMessage` tool schemas load (they are deferred tools — load them via ToolSearch first), the launched masters appear in `ListAgents` (their name is the tab name passed as `--name`; allow 2-3 minutes after launch), and `notify_when_idle` is accepted.
- Always keep a **fallback** `ScheduleWakeup(3600)` (the maximum is one hour) and call it at the end of every turn.
- Notifications fire **once**: resubscribe every master that isn't done. Subscriptions expire after 12 hours: resubscribe on fallback wakes.
- Subscribe from the main conversation, not from a subagent (subagent subscriptions don't take).
- **Idle ≠ done.** A master is also idle while asking a question, after a context run-out, or when blocked. The notification is a reason to look, not evidence.
- **poll** mode (any condition missing): `ScheduleWakeup` 20 min, then 30 min.

Count `idle_cycles` only on fallback / poll wakes with no change; after 3, stop sleeping and wait for the user.

## 2. Liveness from commits and the working tree (the truth)

The branches don't lie. A session that's working is committing or changing files:

```bash
git rev-list --count plan/<id> ^main            # commits ahead of main
git -C .worktrees/<id> status --porcelain        # uncommitted work in progress
git log --all --oneline --since='25 minutes ago' | grep 'plan-'
git log main..plan/<id> --oneline --grep 'mark done'   # done (limit to main..plan/<id>!)
```

- **Don't** use the presence of the session's conversation-log directory as a liveness signal — a session made two commits before its directory appeared.
- **Don't** judge in the first 1-2 minutes after launch — the first response takes a while.
- Survives crashes: commits are real even if the terminal died.

## 3. The inbox (what happened)

Masters append a short report to `.claude/plans/inbox.md` and commit it on done / blocked / cancelled, and file execution requests there too. On every wake the orchestrator reads it in **three places**: each plan branch's inbox (`git log main..plan/<id> -p -- .claude/plans/inbox.md`), main's inbox, and each worktree's uncommitted inbox diff (`git -C .worktrees/<id> diff -- .claude/plans/inbox.md`). Requests were missed for hours when only one place was checked.

## 4. "Waiting for the user" board (where to look)

A small set of Claude Code hooks can maintain a shared list of sessions waiting on the user:

| Hook event | Board |
|---|---|
| `Notification` with `permission_prompt` | add "waiting for permission" |
| `Notification` with `idle_prompt` (no input for ~60 s after a reply) | add "waiting for reply" with the last message's first line |
| `UserPromptSubmit` / `Stop` / `SessionEnd` | remove |

Name each entry by the tab name the launcher assigned (`M:<project>/<id> <task>`). On wake the orchestrator reads the board and tells the user only **where** to look — "plan `auth-001` is waiting for you since 14:20 — open tab `M:myapp/auth-001 …`" — never the question itself (the master talks to the user directly). Sessions that are merely sleeping under `/loop` aren't "waiting".

Masters additionally stamp `last_activity` (HH:MM) and, if the user is away, `status: waiting-user` on their row of the `_progress.md` snapshot at checkpoints. That's a fallback if you don't install the hooks.

## Detecting "Wave done" reliably

A Wave is done when every row is `done` / `cancelled` / `blocked`. A completed plan leaves two traces on its branch: the `<id>-<slug>_done.md` file and the `chore(plan-<id>): mark done` commit (the source of truth). If a row says `implementing` but the branch has the mark-done commit, the report was missed — read the plan MD's execution log or the branch's inbox.

## What this pattern deliberately does NOT do

- **No busy polling.** Notifications plus a 60-min fallback.
- **No automatic re-launch.** A stale session is surfaced, not auto-restarted. Re-launching is a user decision (the execution log says where it stopped) — and never while the old master is still running.
- **No relaying via messages.** Messages are wake-up hints. They can expire unseen when the two sides run in different permission modes, and they are never user approval. The content of record is the committed inbox.

## TL;DR

1. Subscribe to masters' idle notifications; 60-min fallback wake; poll 20-30 min only if notifications are unavailable.
2. Liveness = commits + worktree changes. Not log directories, not the first minute.
3. Read the inbox in all three places on every wake.
4. Tell the user which tab is waiting — never relay the question.
5. Surface stale sessions; don't auto-restart.
