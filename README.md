# claude-wave-orchestration

Parallel orchestration method for [Claude Code](https://claude.com/claude-code) using **Wave-based session launching**, **batch judgment sessions**, and **independent worktrees**. Born from a real 5-day operation that cleared ~120 backlog plans across a production codebase.

## TL;DR

You have a backlog of 100+ plans / refactors / draft tickets and a single Claude Code instance feels like a bottleneck. This repo offers a method that:

- Launches **10 independent Claude Code sessions in parallel** (each in its own `git worktree`)
- Coordinates them through a single **`_progress.md` dashboard** managed by an orchestrator session
- Uses **"Wave" cycles** (10 sessions × N iterations) instead of trying to keep everything in one head
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
| [`templates/`](templates/) | Drop-in templates (orchestrator bootstrap, INSTRUCTIONS.md, plan MD, _progress.md, starter prompt) |
| [`scripts/launch_claude.py`](scripts/launch_claude.py) | Standalone session launcher for Windows Terminal + Claude CLI |
| [`examples/case-study-anonymized.md`](examples/case-study-anonymized.md) | Anonymized walkthrough of the original engagement |

## Quick start (5 min)

### Prerequisites
- Claude Code CLI installed and authenticated
- Windows Terminal (`wt`) on Windows, or modify the launcher for `tmux` / `iTerm`
- Git with worktree support (any modern version)
- A backlog you want to clear — typically as a folder of plan Markdown files

### Setup
```bash
# 1. Drop the templates into your project
cp claude-wave-orchestration/templates/INSTRUCTIONS.md  YOUR_PROJECT/.claude/plans/
cp claude-wave-orchestration/templates/progress-template.md  YOUR_PROJECT/.claude/plans/_progress.md

# 2. Add launcher
cp claude-wave-orchestration/scripts/launch_claude.py  ~/bin/   # or wherever

# 3. Ignore worktrees and active progress in your project
echo ".worktrees/" >> YOUR_PROJECT/.gitignore
```

### Starting the orchestrator

The "orchestrator" is one Claude Code session that coordinates everything. You start it by **opening Claude Code in your project directory and pasting the bootstrap prompt**.

```
cd YOUR_PROJECT
claude              # opens Claude Code in this directory
```

Then paste the contents of [`templates/orchestrator-bootstrap-prompt.md`](templates/orchestrator-bootstrap-prompt.md) (the block under "Copy from here") as the first message.

The bootstrap prompt tells this session:

- **Its role**: orchestrator only — never writes feature code
- **What to read first**: `INSTRUCTIONS.md`, `_progress.md`, the pattern docs
- **The operating loop**: pick Wave → launch sessions → collect summaries → update dashboard → repeat
- **The constraints**: don't push to main, don't talk to sessions directly, don't implement
- **What to do when**: completion summaries arrive, the user asks "what's next?", the user asks "how are we doing?"

The orchestrator's first response after reading the bootstrap will typically be a scan of your plans folder and a proposed Wave 1.

### How the orchestrator launches each session

For each plan in a Wave, the orchestrator runs:

1. `git worktree add .worktrees/<area>-<NNN> -b plan/<area>-<NNN> integration/latest-known-good` — isolated workspace (base on `origin/main` only for Wave 1)
2. Copies the plan MD + `INSTRUCTIONS.md` + `_progress.md` into the worktree
3. `python launch_claude.py <worktree-path> "<starter prompt>"` — opens a new terminal with a dedicated Claude Code session

The "starter prompt" given to each session tells *it* (the session master, not the orchestrator) things like:

- "You are a dedicated session for plan {area}-{NNN}" (e.g. `auth-001`)
- "Your worktree is .worktrees/{area}-{NNN}/, your branch is plan/{area}-{NNN}"
- "First read these files: INSTRUCTIONS.md, your plan MD, _progress.md"
- "You may talk to the user directly and **commit** — that's the end of your responsibility"
- "Don't push, don't open PRs, don't merge to main (all the user's call); don't edit other worktrees"
- Plan-specific context (1-2 sentences)

A session master's landing authority stops at `commit`. push / PR / merge to main are all left to the user. (Deploying from the worktree for verification only is allowed.) When a plan is done, the session **renames its file to `<id>-<slug>_done.md`** rather than flipping a Status field.

See [`templates/starter-prompt-template.md`](templates/starter-prompt-template.md) for the full template with variants for batch sessions, audit sessions, and INDEX-closing sessions.

### One Wave (what the orchestrator does for you)

The orchestrator runs the steps below for each plan in a Wave. Shown here for transparency — you don't normally type these by hand:

```bash
# For each plan ID in this wave (e.g. 10 of them):
PLAN_ID=auth-001                                         # the plan you're launching (area-NNN)
PLAN_FILE=$(ls .claude/plans/${PLAN_ID}-*.md | head -1)  # find the matching plan MD

# 1. Create an isolated worktree on a fresh branch off the integration branch
#    (use origin/main only on Wave 1, before integration/latest-known-good exists)
git worktree add .worktrees/${PLAN_ID} -b plan/${PLAN_ID} integration/latest-known-good

# 2. Copy the plan MD and shared files into the worktree
mkdir -p .worktrees/${PLAN_ID}/.claude/plans
cp "${PLAN_FILE}"                  .worktrees/${PLAN_ID}/.claude/plans/
cp .claude/plans/INSTRUCTIONS.md   .worktrees/${PLAN_ID}/.claude/plans/
cp .claude/plans/_progress.md      .worktrees/${PLAN_ID}/.claude/plans/

# 3. Build the starter prompt and launch
PLAN_FILENAME=$(basename "${PLAN_FILE}")
STARTER=$(sed "s|{PLAN_ID}|${PLAN_ID}|g; s|{PLAN_FILENAME}|${PLAN_FILENAME}|g" \
              templates/starter-prompt-minimal.txt)
python launch_claude.py .worktrees/${PLAN_ID} "${STARTER}"
```

(Save your minimal starter prompt as `templates/starter-prompt-minimal.txt` — see [templates/starter-prompt-template.md](templates/starter-prompt-template.md) for variants.)

Sessions are independent. Each one talks to the user directly, commits when ready (it does **not** push — that's the user's call), and updates its row in `_progress.md`.

The **orchestrator session** (the one you started this from) collects summaries, refreshes the master `_progress.md`, and decides what goes in the next Wave.

## The patterns at a glance

**[Wave strategy](patterns/wave-strategy.md)** — Don't launch all 100 sessions at once. Launch 10. Wait for completion. Use what you learned to plan the next 10.

**[Batch sessions](patterns/batch-sessions.md)** — When you have 10+ trivially-similar plans (e.g. "draft v2 plans, are these still relevant?"), one session can judge all of them. These are orchestration-meta work, so they use the `meta-` area prefix (e.g. `meta-001`). We retired 50+ plans this way.

**[Implicit done detection](patterns/implicit-done-detection.md)** — Many plans labeled "TODO" are already finished by past commits. A Wave session whose only job is to verify this is faster than re-implementing.

**[INDEX done pattern](patterns/index-done-pattern.md)** — Once an INDEX plan's children are all done, the INDEX session writes a summary table and closes — no new code. We did this 7 times in a row.

**[Main merge strategy](patterns/main-merge-strategy.md)** — When you have 90 orphan `plan/<id>` branches, don't merge them naively. Find or create a single "integration branch" that already harmonizes the conflicts. We used a `plan/999b` branch with 366/366 tests passing as the merge starting point. Also covers **between-Wave integration** — merging each Wave forward so the next isn't based on stale `main`.

**[Test Waves](patterns/test-waves.md)** — Interleave a verification-only Wave every ~3 build Waves so test debt stays bounded instead of detonating at deploy time.

**[Session monitoring](patterns/session-monitoring.md)** — Lightweight liveness tracking: a `last_activity` heartbeat plus `git log --all --since=1h` so stalled or dead sessions surface without polling.

## When NOT to use this method

- **Backlog < 20 items**: overhead exceeds benefit. Use single sessions.
- **Plans require deep cross-cutting coordination** (e.g. one big refactor split across the team): the independent-worktree model causes pain. Use a single session or coordinated PRs.
- **You can't dedicate ~hours/day to orchestration**: this is parallel but not autonomous. Sessions ask the user real questions.
- **Your CI/CD won't tolerate dozens of branches**: see [ANTI-PATTERNS.md](ANTI-PATTERNS.md) on the merge bottleneck.

## Origin

This method was developed during a real 5-day engagement on a production multi-tenant SaaS codebase (Python / Flask / Cloud Run). See [examples/case-study-anonymized.md](examples/case-study-anonymized.md) for the full story.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

The method is still young. PRs, issues, and forks welcome. Especially valuable:

- Adaptations for non-Windows environments (the launcher uses Windows Terminal)
- Adaptations for non-Claude AI assistants
- Tooling that automates the orchestrator's `_progress.md` updates
- Patterns we missed
