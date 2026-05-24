# Methodology

The full method, in depth. Read [README.md](README.md) first for the elevator pitch.

## 1. The problem this method solves

You have a project with:

- A lot of work tracked in plan files (Markdown tickets, RFCs, issues exported to MD, etc.)
- Plans accumulate faster than you clear them
- Many "TODO" plans turn out to be already done by past commits — but you don't know which
- Sequential, single-session work doesn't scale to your backlog

Symptoms you might recognize:

- Your `.claude/plans/` or equivalent folder has 50+ files and you can't tell which are alive
- You implement something, only to discover it was done last month
- Your single Claude Code session burns context arguing about plans rather than executing them
- You want progress but can't watch a single session all day

## 2. The mental model

Think of it as a **parallel pipeline** with three roles:

```
┌─────────────────────┐
│ Orchestrator        │  ← One session. You start here.
│ (this session)      │     - Decides what's in each Wave
│                     │     - Updates the master _progress.md
└──────────┬──────────┘     - Never writes feature code
           │
           │ launches via launch_claude.py
           ▼
┌─────────────────────┐    ┌─────────────────────┐
│ Main session #1     │    │ Main session #2     │  ... (N parallel)
│ in .worktrees/A/    │    │ in .worktrees/B/    │
│ branch plan/A       │    │ branch plan/B       │
│                     │    │                     │
│ Owns plan A end to  │    │ Owns plan B end to  │
│ end. Talks to user  │    │ end. Talks to user  │
│ directly. Commits,  │    │ directly. Commits,  │
│ pushes, opens PR.   │    │ pushes, opens PR.   │
└──────────┬──────────┘    └──────────┬──────────┘
           │                          │
           │ summary at completion    │
           ▼                          ▼
        (back to orchestrator for next Wave)
```

Three properties make this work:

1. **Worktree isolation** — Each session works in its own `.worktrees/<plan_id>/` directory on its own branch. They cannot step on each other.
2. **Single source of truth** — `_progress.md` lives in the orchestrator's working directory only. Worktree copies are read-only references.
3. **Direct user dialogue per session** — Main sessions talk to the user without going through the orchestrator. The orchestrator handles state, not conversation.

## 3. Roles in detail

### Orchestrator (one session)

**Does:**
- Decides what goes in each Wave
- Creates worktrees with `git worktree add`
- Launches sessions with `launch_claude.py`
- Receives completion summaries from sessions (the user pastes them)
- Updates the master `_progress.md` (one row per session)
- Plans the next Wave based on what was discovered
- Identifies cross-cutting issues that emerge across sessions

**Does NOT:**
- Write feature code
- Commit or push to branches other than chore-level orchestration updates
- Make architectural decisions on individual plans
- Talk to sessions directly (they're independent processes)

The orchestrator is the **conductor**, not a performer.

### Main session (one per plan, N parallel)

**Does:**
- Owns the plan it was launched with, from start to "done" or "cancelled"
- Talks to the user directly when needed
- Commits, pushes, opens PRs as appropriate (see [PR/push policy](#prpush-policy))
- Updates its own row in `_progress.md` (and in the worktree copy)
- Sometimes discovers the plan is already done — judges it "implicit done"
- Sometimes discovers the plan should be canceled — judges it "cancelled" with reasoning
- Reports back when finished

**Does NOT:**
- Edit other sessions' worktrees
- Push to main directly
- Make decisions outside its plan's scope (escalates to user or noted as "out of scope")

### User

**Does:**
- Reviews plans before they enter a Wave (optional but recommended)
- Responds to questions sessions ask (each session has its own conversation)
- Approves PRs and merges
- Pastes session completion summaries to the orchestrator
- Decides when to start the next Wave

**Does NOT need to:**
- Watch every session
- Make every decision (sessions decide cancelled vs done with reasoning)
- Manually track progress (`_progress.md` does that)

## 4. Wave anatomy

A "Wave" is **one cycle of: plan → launch → execute → summarize → integrate**.

```
Wave start
   │
   │ Orchestrator picks N plans (typically 10) for this Wave
   │
   ▼
1. CREATE worktrees for each plan (git worktree add)
   │
   ▼
2. SEED each worktree with INSTRUCTIONS.md + plan_<id>.md + _progress.md
   │
   ▼
3. LAUNCH sessions with launch_claude.py, 5-6 sec apart
   (5 sec keeps prompt cache warm; longer if hitting .claude.json locks)
   │
   ▼
4. SESSIONS WORK independently — orchestrator does NOT poll
   │
   │   ┌──────────────────────────────┐
   │   │ User receives questions per  │
   │   │ session, answers them, then  │
   │   │ pastes the final summary to  │
   │   │ orchestrator                 │
   │   └──────────────────────────────┘
   ▼
5. ORCHESTRATOR receives each summary as it arrives
   - Edits one row in _progress.md
   - Notes cross-cutting issues
   - Acknowledges in 2-3 sentences
   │
   ▼
6. WAVE DONE when all N rows are done/cancelled/blocked
   │
   ▼
7. ORCHESTRATOR plans next Wave
   - Includes follow-up items found by this Wave
   - May spawn new plans (e.g. for issues discovered mid-session)

Wave end
```

### Wave sizing

We used Waves of **8-12** sessions consistently. Rationale:

- **<8**: orchestrator under-utilized; user could just run a single session
- **8-12**: sweet spot — enough parallelism to feel fast, few enough to keep `_progress.md` mentally tractable
- **>12**: prompt-cache contention on `.claude.json`, user overwhelmed by simultaneous conversations

### Wave content selection

For a given Wave, prefer plans that are:

- **Independent** of each other (so failures don't cascade)
- **Mixed in domain** (so user's mental load varies, not 10 of the same kind of decision)
- **Of varying expected difficulty** (so a couple finish fast and create momentum)

Don't avoid plans with dependencies on previous Waves — sessions handle that with `blocked on <id>` annotations gracefully.

## 5. The `_progress.md` contract

This file is the only thing that needs to be consistent across all 100+ sessions. Treat it carefully.

### Structure

```markdown
# <Project> — Plan completion operation dashboard

**Started**: YYYY-MM-DD
**Goal**: Move all plans in <plans dir> to done or cancelled

## Conventions
- worktree path: ...
- branch: plan/<id>
- base: origin/main

## Status legend
- draft / ready / in_progress / done / cancelled / blocked

## Wave N (YYYY-MM-DD)

| ID | Title | wave | status | launched_at | branch | notes |
|---|---|---|---|---|---|---|
| 100 | Add feature X | 1 | done | 2026-... | plan/100 | commit abc123, PR #5 |
| 101 | Refactor Y | 1 | blocked | 2026-... | plan/101 | blocked on 100 |
...

## Execution log

YYYY-MM-DD
- HH:MM Wave 1 launched: 100, 101, ...
- HH:MM Wave 1 landed: 8 done, 1 cancelled, 1 blocked
```

### Update rules

1. **The orchestrator owns the master copy.** Period. The orchestrator's working directory is canonical.
2. **Each worktree gets a read-only snapshot** seeded at launch. Sessions reference it for context but their edits are local.
3. **Sessions update their own row** in the worktree copy (for self-tracking) but the orchestrator re-applies the change to the master after receiving the summary.
4. **Don't try to merge `_progress.md` from branches.** It will conflict in 80+ places. Just add it to `.gitignore` if necessary, or maintain it as orchestrator-only state.

This is the single biggest gotcha. See [ANTI-PATTERNS.md](ANTI-PATTERNS.md).

## 6. PR/push policy

Establish this on Day 1, not Day 5 (we learned this the hard way):

| Case | push | PR |
|---|---|---|
| New feature / large implementation | **required** | **recommended** |
| New plan MD / docs only (chore) | recommended | not needed |
| Implicit done verdict (no code change) | recommended | not needed |
| Bug fix | **required** | **recommended** |
| **Tests added alone** | **required** | **not needed** (if you plan a dedicated test phase) |
| **Security / fallback removal** | **required** | **required** |
| INDEX done verdict | recommended | not needed |
| Cancelled verdict | recommended | not needed |

The "PR" column matters because reviewing 80 PRs at once is hellish. Force PRs only where it really matters; for everything else the orchestrator (or you) can review by scanning branches.

## 7. Patterns to use

These are detailed in [patterns/](patterns/) but here's the index:

- **[Wave strategy](patterns/wave-strategy.md)** — How to size, sequence, and content-mix Waves
- **[Batch sessions](patterns/batch-sessions.md)** — Consolidating 10+ trivial judgments into one session (the "999 family" pattern)
- **[Implicit done detection](patterns/implicit-done-detection.md)** — Verify rather than re-implement
- **[INDEX done pattern](patterns/index-done-pattern.md)** — Closing parent INDEX plans once children are settled
- **[Main merge strategy](patterns/main-merge-strategy.md)** — Resolving the 90-orphan-branches problem

## 8. Lifecycle of a typical plan

```
draft → ready → in_progress → done | cancelled

with side detours through:
  → blocked (record reason; orchestrator may reassign or wait)
  → "implicit done" verdict (no code change, just status flip + audit trail)
  → INDEX consolidation (close once children are done)
```

The session decides which path. The orchestrator records what happened.

## 9. When does the operation end?

When `_progress.md` shows zero rows that are still `draft`, `ready`, or `in_progress`. Everything is `done`, `cancelled`, or `blocked` with a clear external dependency.

You can also declare "phase complete" at any natural stopping point — the method is not all-or-nothing.

## 10. After the operation

Things that need to happen after the last Wave:

1. **Main merge orchestration** — 80+ branches don't merge themselves. See the pattern doc.
2. **Comprehensive testing** — Sessions skipped detailed testing in favor of velocity. Now's the time for the QA phase.
3. **Deployment** — All your work is on branches. Get it to production.
4. **Memory / knowledge consolidation** — The orchestrator may have accumulated valuable cross-cutting observations. Distill them into your project's living docs.

These are typically separate operations from "clearing the backlog." Don't conflate them.

## 11. Cost considerations

10 parallel Claude Code sessions = 10x API calls during peak.

- Use Claude Code's built-in token caching aggressively (the 5-minute prompt cache window)
- Stagger session launches by 5-6 seconds (gives cache time to populate)
- Keep starter prompts short and consistent (better cache hit rate)
- For "implicit done" verdicts, a session may use 1/10th the tokens of a full implementation session — these are very cheap

In our case, the 5-day operation closed ~120 plans. The token cost was significant but well below the value delivered.
