# claude-wave-orchestration

Parallel orchestration method for [Claude Code](https://claude.com/claude-code) using **Wave-based session launching**, **batch judgment sessions**, and **independent worktrees**. Born from a real 5-day operation that cleared ~120 backlog plans across a production codebase.

## TL;DR

You have a backlog of 100+ plans / refactors / draft tickets and a single Claude Code instance feels like a bottleneck. This repo offers a method that:

- Runs **independent Claude Code sessions in parallel** (each in its own `git worktree`), in Waves of 8-12 plans with 3-6 running at once
- Splits the work into three roles: a **planner** turns raw problems into plans, **session masters** implement one plan each up to `commit`, and one **orchestrator** launches, integrates, deploys and verifies
- Coordinates them through files — a **`_progress.md` dashboard** (orchestrator-only), an append-only **`inbox.md`** for reports, and per-plan **`STARTER.md`** mission briefs — with idle notifications to wake the orchestrator
- Uses **"Wave" cycles** instead of trying to keep everything in one head
- Introduces **"batch sessions"** that consolidate dozens of trivial decisions into one session
- Establishes the **"implicit done"** pattern — many plans turn out to be already done by past work; rapid audit beats reimplementation

In a real engagement, this method moved **~120 plans from draft/blocked to done/cancelled in 5 days** with sustained quality and clear paper trail.

## Why this exists

Single-session Claude Code (or any AI assistant) hits walls when:

- The backlog is too big to keep in one context window
- Plans have hidden dependencies you only discover mid-implementation
- Many "TODO" plans are actually completed but unaudited
- Sequential execution is too slow for the user's pace
- The user wants visibility into progress without micromanaging

This method addresses all of the above by **horizontally scaling sessions** and **vertically simplifying the orchestrator's job**.

## What's in this repo

| Path | What |
|---|---|
| [`METHODOLOGY.md`](METHODOLOGY.md) | The full method explained, with rationale |
| [`ANTI-PATTERNS.md`](ANTI-PATTERNS.md) | What went wrong, what to avoid |
| [`patterns/`](patterns/) | Composable patterns (Wave, batch, INDEX, merge, implicit-done) |
| [`templates/`](templates/) | Drop-in templates (INSTRUCTIONS.md, STARTER.md, plan MD, _progress.md, starter prompt, orchestrator bootstrap) |
| [`scripts/launch_claude.py`](scripts/launch_claude.py) | Standalone session launcher (Windows Terminal; iTerm2 / tmux minimal) with role-based tab names and colors |
| [`scripts/collect_fix_inputs.py`](scripts/collect_fix_inputs.py) | Collects new fix seeds (failed verify, open backlog lines, full-suite failures) for a scheduled planner run; used via the launcher's `--prompt-script` |
| [`examples/case-study-anonymized.md`](examples/case-study-anonymized.md) | Anonymized walkthrough of the original engagement |

## Quick start (5 min)

### Prerequisites
- Claude Code CLI installed and authenticated
- Windows Terminal (`wt`) on Windows, or modify the launcher for `tmux` / `iTerm`
- Git with worktree support (any modern version)
- A backlog you want to clear — typically as a folder of plan Markdown files

### Setup
```bash
# 1. Drop the templates into your project and commit them to the base branch
#    (worktrees only receive committed files)
mkdir -p YOUR_PROJECT/.claude/plans
cp claude-wave-orchestration/templates/INSTRUCTIONS.md      YOUR_PROJECT/.claude/plans/
cp claude-wave-orchestration/templates/progress-template.md YOUR_PROJECT/.claude/plans/_progress.md
touch YOUR_PROJECT/.claude/plans/inbox.md YOUR_PROJECT/.claude/plans/_backlog.md

# 2. Add the launcher
cp claude-wave-orchestration/scripts/launch_claude.py  ~/bin/   # or wherever

# 3. Ignore worktrees in your project
echo ".worktrees/" >> YOUR_PROJECT/.gitignore

# 4. Make tests safe to run from parallel sessions: an exclusive wrapper that
#    queues runs, and a scheduled full-suite run once a day
```

The method is packaged as Claude Code skills — `session-planner`, `session-orchestrator`, `session-master` — kept in the user-level skills folder (`~/.claude/skills/`). This repo is the method and the templates they reference; where they differ, the skills win. Without the skills, use [`templates/orchestrator-bootstrap-prompt.md`](templates/orchestrator-bootstrap-prompt.md) and [`templates/starter-prompt-template.md`](templates/starter-prompt-template.md).

### Choosing how to start a session

First settle four things: **purpose, completion criteria, scope, and what must not be touched**. Then pick the type:

| Type | When | Command |
|---|---|---|
| single | Normal work in one project (the default) | `python launch_claude.py ../myapp --role single --task "<summary>" "<prompt>"` |
| planner | No plan yet — investigate a problem and file plans | `python launch_claude.py ../myapp --role planner --task "<summary>" "/session-planner <problem>"` |
| orchestrator | Plans exist; run many of them in parallel | `python launch_claude.py ../myapp --role orchestrator --task "<summary>" --effort medium "/loop /session-orchestrator <instructions>"` |

From Git Bash, prefix commands whose prompt starts with `/` with `MSYS_NO_PATHCONV=1` (otherwise MSYS rewrites `/loop` into a Windows path).

The tab name — also the Remote Control name and the `--name` used for cross-session messages — is `<O|M|P|S>:<project>[/<plan-id>] <task>`, colored by role (orchestrator purple, master blue, planner green, single grey). Colors mean the role, never the state. Use Opus for every role by default.

### Starting the orchestrator

The orchestrator **must run under `/loop`** (it sleeps between patrols with `ScheduleWakeup`) and at `--effort medium` (most patrols find nothing new; ask for more effort only for deep decisions). Its first response is typically a scan of `.claude/plans/` and a proposed Wave 1 for you to approve.

The orchestrator:

- **launches and integrates** — never writes feature code; any raw problem or "compare / research / how should we" question goes to a planner
- **asks you** before every new Wave, next plan, merge and deploy (once per batch)
- **reads reports from the inbox** — you don't paste anything between tabs
- **deploys alone**, from main, then verifies; failures come back as fix plans from a planner

### How the orchestrator launches each master

For each plan in a Wave (you don't normally type these by hand):

```bash
ID=auth-001
PLAN_FILE=$(ls .claude/plans/${ID}-*.md | head -1)

# 1. Isolated worktree on a fresh branch off the integration branch
#    (origin/main only on Wave 1, before integration/latest-known-good exists)
git worktree add .worktrees/${ID} -b plan/${ID} integration/latest-known-good

# 2. Seed: cp ONLY the plan MD (INSTRUCTIONS.md / _progress.md / inbox.md are tracked
#    and come with the worktree — copying them from the root can overwrite them)
mkdir -p .worktrees/${ID}/.claude/plans
cp "${PLAN_FILE}" .worktrees/${ID}/.claude/plans/

# 3. Generate .worktrees/${ID}/.claude/plans/STARTER.md from templates/starter-md-template.md

# 4. Pre-launch check (b3): plan MD present, STARTER.md is for ${ID}, no tracked file
#    modified, no master for ${ID} still running — otherwise don't launch

# 5. Launch (one-line prompt; context lives in STARTER.md)
PLAN_TITLE=$(grep -m1 '^# ' "${PLAN_FILE}" | sed -e 's/^# *//')
MSYS_NO_PATHCONV=1 python launch_claude.py "$(pwd -W)/.worktrees/${ID}" \
  --role master --plan-id "${ID}" --task "${PLAN_TITLE}" \
  "/session-master ${ID}（.claude/plans/STARTER.md を読んで開始）"
sleep 6
```

Each master reads STARTER.md, implements, asks you questions directly in its own tab, and commits. Its landing authority **stops at commit**: no push, PR, merge or deploy — checks that need a deploy are written as `verify:` in its report. On completion it appends a short report to `.claude/plans/inbox.md`, commits, and finally renames its plan to `<id>-<slug>_done.md` (`chore(plan-<id>): mark done`).

The orchestrator wakes on the masters' idle notifications (60-min fallback), reads the inbox, updates `_progress.md`, files new issues into `_backlog.md`, archives done plans to `docs/specs/`, stops finished masters and removes their worktrees. With your approval it merges, deploys main, and verifies:

```
ready → implementing → done → merged → deployed → verified
```

## The patterns at a glance

**[Wave strategy](patterns/wave-strategy.md)** — Don't launch all 100 sessions at once. Launch 10. Wait for completion. Use what you learned to plan the next 10.

**[Batch sessions](patterns/batch-sessions.md)** — When you have 10+ trivially-similar plans (e.g. "draft v2 plans, are these still relevant?"), one session can judge all of them. These are orchestration-meta work, so they use the `meta-` area prefix (e.g. `meta-001`). We retired 50+ plans this way.

**[Implicit done detection](patterns/implicit-done-detection.md)** — Many plans labeled "TODO" are already finished by past commits. A Wave session whose only job is to verify this is faster than re-implementing.

**[INDEX done pattern](patterns/index-done-pattern.md)** — Once an INDEX plan's children are all done, the INDEX session writes a summary table and closes — no new code. We did this 7 times in a row.

**[Main merge strategy](patterns/main-merge-strategy.md)** — Merge as plans finish (with user approval) instead of letting 90 orphan `plan/<id>` branches pile up; resolve conflicts by file type (union only append-only files like `inbox.md`); never merge during a deploy. Also covers the heavy main-merge if branches did pile up.

**[Test Waves](patterns/test-waves.md)** — One test run at a time, no full suite in sessions, a scheduled full suite once a day, and a verification-only Wave every ~3 build Waves so test debt stays bounded.

**[Session monitoring](patterns/session-monitoring.md)** — Wake on idle notifications, judge liveness from commits and worktree changes, and tell the user which tab is waiting — without polling.

## When NOT to use this method

- **Backlog < 20 items**: overhead exceeds benefit. Use single sessions.
- **Plans require deep cross-cutting coordination** (e.g. one big refactor split across the team): the independent-worktree model causes pain. Use a single session or coordinated PRs.
- **You can't answer sessions' questions or approve merges/deploys**: this is parallel but not autonomous. Sessions ask the user real questions, and every Wave / merge / deploy needs your OK.
- **Your CI/CD won't tolerate dozens of branches**: see [ANTI-PATTERNS.md](ANTI-PATTERNS.md) on the merge bottleneck.

## Origin

This method was developed during a real 5-day engagement on a production multi-tenant SaaS codebase (Python / Flask / Cloud Run). See [examples/case-study-anonymized.md](examples/case-study-anonymized.md) for the full story.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

The method is still young. PRs, issues, and forks welcome. Especially valuable:

- Adaptations for non-Windows environments (the launcher is built around Windows Terminal; iTerm2 / tmux support is minimal)
- Adaptations for non-Claude AI assistants
- Tooling that automates the orchestrator's `_progress.md` updates
- Patterns we missed
