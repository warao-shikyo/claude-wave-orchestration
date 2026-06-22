# Methodology

The full method, in depth. Read [README.md](README.md) first for the elevator pitch.

## 0. Kickoff: capture the baseline

Before launching Wave 1, make three decisions that are cheap upfront and expensive to retrofit (we retrofitted all three — ANTI-PATTERNS #1, #3, #11):

1. **Deployment baseline** — Record what is actually live in production now (commit/tag per environment). "Code in a branch" ≠ "running in production"; sessions report deploy status as `none` / `verified-on-deploy` / `live`. Store it at the top of [`_progress.md`](templates/progress-template.md).
2. **Landing model** — Session masters carry plans to **commit only**; push / PR / merge to main are the user's call (see [§6](#6-landing-model)). This is fixed by the skill, but state it in the starter-prompt template so every session sees it.
3. **Integration target** — Decide where Wave results land between Waves (default: an `integration/latest-known-good` branch). See [§4 step 6.5](#4-wave-anatomy).

Also fix the **naming convention** up front: the area-prefix scheme `<area>-<NNN>-<slug>.md` (e.g. `auth-001-oauth-login.md`), branch `plan/<area>-<NNN>`, worktree `.worktrees/<area>-<NNN>/`. Systems are distinguished by area word (`auth`, `billing`, `ui`, …), never by number band. The `meta-` area is reserved for orchestration-meta plans.

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
│ directly. Commits   │    │ directly. Commits   │
│ (push/PR/merge =    │    │ (push/PR/merge =    │
│ user's call).       │    │ user's call).       │
└──────────┬──────────┘    └──────────┬──────────┘
           │                          │
           │ summary at completion    │
           ▼                          ▼
        (back to orchestrator for next Wave)
```

Three properties make this work:

1. **Worktree isolation** — Each session works in its own `.worktrees/<area>-<NNN>/` directory on its own branch. They cannot step on each other.
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
- **Commits** — that's the end of its landing authority (see [§6 landing model](#6-landing-model))
- May deploy from its worktree for **verification only** (not a git push/merge)
- Marks done by **renaming its plan file to `<id>-<slug>_done.md`** (not by flipping a Status field)
- Updates its own row in `_progress.md` (and in the worktree copy)
- Sometimes discovers the plan is already done — judges it "implicit done"
- Sometimes discovers the plan should be canceled — judges it "cancelled" with reasoning
- Reports back when finished

**Does NOT:**
- Push, open PRs, or merge to main (all the user's call)
- Edit other sessions' worktrees
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
4. SESSIONS WORK independently — orchestrator does NOT busy-poll.
   After launching the whole wave, the orchestrator sleeps 20 min
   (ScheduleWakeup), then wakes to check for _done files + new commits.
   Up to 3 idle cycles (≈60 min), then it stops and waits for the user.
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
6.5 INTEGRATE this Wave into integration/latest-known-good (see below)
   │
   ▼
7. ORCHESTRATOR plans next Wave
   - Files every summary's new-issues + residual into the backlog (mandatory)
   - Launching a follow-up plan session needs the user's OK first
   - Periodically archives _done plans into docs/specs/<id>-<slug>.md
   - Every ~3rd Wave, schedule a TEST Wave instead of a build Wave

Wave end
```

### Orchestrator landing & follow-up rules

- **Always file new issues / residual work into the backlog.** Each session's `new-issues` and `residual` fields go into the candidate-plans list (or `docs/backlog.md`). Never swallow them.
- **Don't auto-spawn follow-up sessions.** When a backlog item is ready to become a plan session, ask the user first.
- **Archive done plans as specs.** Periodically (per Wave boundary, or once a few accumulate) move `<id>-<slug>_done.md` into `docs/specs/<id>-<slug>.md` so the work survives as documentation.
- **The orchestrator only commits** `_progress.md` updates, new plan MDs, and `docs/specs` archival — never feature code, never to `plan/<id>` branches.

### Step 6.5 in detail — between-Wave integration

Letting `plan/<id>` branches pile up unmerged is the **#1 anti-pattern**: later Waves base off a stale `origin/main` and re-discover already-fixed bugs. So after each Wave:

1. Merge the Wave's `done` branches into `integration/latest-known-good`, resolving the small conflicts now (~10 branches) rather than later (~90)
2. Base the next Wave's worktrees on that branch

This is **operation-internal** integration; the big, human-driven merge to `main` still happens after the operation ([§10](#10-after-the-operation)). Full mechanics in [main-merge-strategy.md](patterns/main-merge-strategy.md#between-wave-integration-during-the-operation).

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

## Areas
- auth, billing, ui, api, infra, docs, meta (orchestration-meta)

## Conventions
- worktree path: .worktrees/<area>-<NNN>/
- branch: plan/<area>-<NNN>
- base: integration/latest-known-good (origin/main only on Wave 1)

## Status legend
- draft / ready / in_progress / done (= _done file) / cancelled / blocked
- idle_cycles: 0   (consecutive no-change wake cycles; 3 → wait for user)

## Wave N (YYYY-MM-DD)

| ID | Title | wave | status | launched_at | branch | notes |
|---|---|---|---|---|---|---|
| auth-001 | Add feature X | 1 | done | 2026-... | plan/auth-001 | commit abc123, push: no, deploy: none, file: auth-001-...-done |
| billing-002 | Refactor Y | 1 | blocked | 2026-... | plan/billing-002 | blocked on plan-auth-001 |
...

## Execution log

YYYY-MM-DD
- HH:MM Wave 1 launched: auth-001, billing-002, ...
- HH:MM Wave 1 landed: 8 done, 1 cancelled, 1 blocked
```

### Update rules

1. **The orchestrator owns the master copy.** Period. The orchestrator's working directory is canonical.
2. **Each worktree gets a read-only snapshot** seeded at launch. Sessions reference it for context but their edits are local.
3. **Sessions update their own row** in the worktree copy (for self-tracking) but the orchestrator re-applies the change to the master after receiving the summary.
4. **Don't try to merge `_progress.md` from branches.** It will conflict in 80+ places. Just add it to `.gitignore` if necessary, or maintain it as orchestrator-only state.

This is the single biggest gotcha. See [ANTI-PATTERNS.md](ANTI-PATTERNS.md).

## 6. Landing model

The original engagement let each session decide whether to push and open PRs, and it caused churn (ANTI-PATTERNS #3). The method is now simple and fixed by the skill:

> **A session master's landing authority ends at `commit`.** push, PR, and merge to main are **all the user's call.**

| Action | Who |
|---|---|
| Implement + **commit** to `plan/<id>` | session master (on its own judgment) |
| Mark done = rename file to `<id>-<slug>_done.md` + commit | session master |
| Deploy from the worktree for **verification only** | session master (if needed) |
| **push** the branch | user |
| **open a PR** | user |
| **merge to main** / production rollout | user |

Why: if every session pushes / merges independently, branches collide and code rolls back. Keeping each session at commit-only means all the work survives as `plan/<id>` local branches, and the user decides — once, with full context — what merges and when (see [§10](#10-after-the-operation) and [main-merge-strategy.md](patterns/main-merge-strategy.md)).

Sessions report deploy status as `none` / `verified-on-deploy` / `live` in their completion summary, so "code committed" is never confused with "running in production".

## 7. Patterns to use

These are detailed in [patterns/](patterns/) but here's the index:

- **[Wave strategy](patterns/wave-strategy.md)** — How to size, sequence, and content-mix Waves
- **[Batch sessions](patterns/batch-sessions.md)** — Consolidating 10+ trivial judgments into one session (the "999 family" pattern)
- **[Implicit done detection](patterns/implicit-done-detection.md)** — Verify rather than re-implement
- **[INDEX done pattern](patterns/index-done-pattern.md)** — Closing parent INDEX plans once children are settled
- **[Main merge strategy](patterns/main-merge-strategy.md)** — Resolving the 90-orphan-branches problem, plus between-Wave integration
- **[Test Waves](patterns/test-waves.md)** — Interleaving verification Waves so test debt stays bounded
- **[Session monitoring](patterns/session-monitoring.md)** — Lightweight liveness tracking (heartbeat + `git log`)

## 8. Lifecycle of a typical plan

```
draft → ready → in_progress → done | cancelled

with side detours through:
  → blocked (record reason; orchestrator may reassign or wait)
  → "implicit done" verdict (no code change, just _done rename + audit trail)
  → INDEX consolidation (close once children are done)
```

`done` is expressed by renaming the plan file to `<id>-<slug>_done.md` and committing; `cancelled` / `blocked` are written as `## Status` edits with a reason. The session decides which path. The orchestrator records what happened.

## 9. When does the operation end?

When `_progress.md` shows zero rows that are still `draft`, `ready`, or `in_progress`. Everything is `done`, `cancelled`, or `blocked` with a clear external dependency.

You can also declare "phase complete" at any natural stopping point — the method is not all-or-nothing.

## 10. After the operation

Things that need to happen after the last Wave:

1. **Main merge orchestration** — 80+ branches don't merge themselves. See the pattern doc. (If you followed [§4 step 6.5](#4-wave-anatomy), most are already integrated into `integration/latest-known-good`, so this is far smaller.)
2. **Final comprehensive test pass** — If you ran [test Waves](patterns/test-waves.md) every ~3 Waves, this is *confirmation*, not *discovery*: most regressions were already caught and re-filed as plans during the operation. If you deferred all testing, this is the dreaded all-at-once QA phase — schedule it explicitly, don't let it float.
3. **Deployment** — All your work is on branches/integration. Get it to production, and update the deployment baseline (§0) to match reality.
4. **Memory / knowledge consolidation** — The orchestrator may have accumulated valuable cross-cutting observations. Distill them into your project's living docs.

These are typically separate operations from "clearing the backlog." Don't conflate them.

## 11. Cost considerations

10 parallel Claude Code sessions = 10x API calls during peak.

- Use Claude Code's built-in token caching aggressively (the 5-minute prompt cache window)
- Stagger session launches by 5-6 seconds (gives cache time to populate)
- Keep starter prompts short and consistent (better cache hit rate)
- For "implicit done" verdicts, a session may use 1/10th the tokens of a full implementation session — these are very cheap

### Tracking cost per session

We originally tracked no per-session cost, so we knew the operation was expensive but not *which* sessions were the expensive ones (ANTI-PATTERN #13). The launcher now appends a record to a launch log on every launch:

```
~/.claude/wave-launch-log.jsonl   (override with WAVE_LAUNCH_LOG)
{"ts": "...", "event": "launch", "plan_id": "415", "project_path": "..."}
```

To reconcile cost:

1. Each line gives a session's start time and plan id
2. Join against Claude Code's own usage report for the same window
3. Attribute tokens to plan ids by launch time

Use this to confirm what we observed by feel: **batch and audit sessions are remarkably cheap per outcome** (often 1/10th of an implementation session). Favor them where the work allows — see [batch-sessions.md](patterns/batch-sessions.md) and [implicit-done-detection.md](patterns/implicit-done-detection.md).

In our case, the 5-day operation closed ~120 plans. The token cost was significant but well below the value delivered.

## 12. Context economy (orchestrator side)

The orchestrator session runs the longest of any session — typically days. Without discipline, its context window fills with summaries, file reads, and acknowledgments faster than you'd expect.

### What inflates the orchestrator's context

- **Re-reading `_progress.md`** for each update (~10 KB per Read)
- **Verbose completion summaries** pasted by the user (~3-5 KB each, ~500 KB for 120 plans)
- **Long acknowledgments** by the orchestrator (~500 chars-1 KB each)
- **Grep / Glob / Bash output** when checking branch state

### What keeps it lean

| Tactic | How much it saves (per summary cycle) |
|---|---|
| Use `Edit` (diff-only) instead of `Read + Write` for `_progress.md` | ~10 KB |
| Short structured summaries from sessions instead of prose | ~3 KB |
| Acknowledge in ≤2 sentences | ~500 chars |
| Avoid spot-checks (`grep`, `git log`) unless the user asks | ~200-500 chars |
| Use Claude Code's prompt cache (default; no action needed) | API cost only, not context |

### Specific instructions for the orchestrator

These should be in your bootstrap prompt (see [`templates/orchestrator-bootstrap-prompt.md`](templates/orchestrator-bootstrap-prompt.md)):

1. **Read `_progress.md` once at startup**, then use `Edit` for every subsequent update
2. **Acknowledge completion summaries in ≤2 sentences**: status updated + 1 cross-cutting observation if any
3. **Don't re-Read files** unless the session's last edit was 30+ minutes ago (assume your "remembered state" is current)
4. **Don't grep/glob unless asked** — the user can see `_progress.md` too if they need full state (the one routine exception is the scheduled 20-min wake-check, which scans for `_done` files and recent `plan-` commits — see [§4](#4-wave-anatomy))
5. **Batch acknowledgments** when 3-4 summaries arrive in succession — one combined response is leaner than four

### Specific instructions for sessions

These should be in your starter prompt template (see [`templates/starter-prompt-template.md`](templates/starter-prompt-template.md)):

Emit **two sections** on completion — one for the user, one for the orchestrator:

```
=== Detailed summary (for the user) ===
[Rich prose: what changed, why, what was discovered, new issues, residual work,
anything cross-cutting. The user reads this for situational awareness. Don't restrain length.]

=== Short summary (paste this to the orchestrator) ===
plan {id} → {done|cancelled|blocked}
commit: {hash} (push: no — commit is the end of responsibility)
verified: unit|integration|manual|deferred
deploy: none|verified-on-deploy|live
done-file: {id}-{slug}_done.md
key: <30-chars take-away>
new-issues: <new issues, 0-3 lines>
residual: <residual work, 0-3 lines>
```

The short section is ~200 chars typical. **Detailed prose stays in the user-facing section + plan MD execution log + commit messages**, not in what the orchestrator processes. The `new-issues` / `residual` fields are mandatory raw material — the orchestrator files them into the backlog.

### Specific instructions for the human (user)

The user is the bridge between sessions and the orchestrator. To keep the orchestrator lean:

1. **Read the detailed summary yourself** — that's where situational awareness lives. The orchestrator never sees it; no context cost.
2. **Paste only the short summary** to the orchestrator. The orchestrator updates `_progress.md` from that.
3. **If you want the orchestrator to track a cross-cutting issue**, mention it explicitly in your next message — don't expect the orchestrator to dig it out of long prose.
4. **Don't ask the orchestrator to recap what happened** unless necessary. Read `_progress.md` yourself if you need full state.
5. **Do ask the orchestrator high-leverage questions**: "what's next?", "should I worry about X across sessions?", "is this plan ready for a Wave?" — these are where the orchestrator's accumulated context pays off.

This is **collaborative discipline**: the user reads, the orchestrator tracks, the two context pools stay separate.

### Why this matters at scale

For a 500-plan operation:

| Discipline | Cumulative orchestrator context |
|---|---|
| No discipline (re-Read + verbose summaries) | ~7.5 MB before compaction |
| Verbose summaries + Edit only | ~2.5 MB |
| Short summaries + Edit only | ~250 KB |
| Short summaries + Edit + batch acks | ~150 KB |

The difference between "no discipline" and "full discipline" is ~50x. A long operation that **never hits compaction** stays fast, coherent, and cheap. One that compacts repeatedly loses fidelity in the orchestrator's mental model — you'll feel it as "wait, what was plan 412 about again?"

### When the orchestrator *should* read full files

- **Operation startup**: read `_progress.md` once to load state
- **After a multi-hour break**: re-read to refresh
- **When the user asks "what's the current state?"**: a fresh read avoids stale snapshots
- **When debugging an Edit failure**: re-read to find the exact `old_string`

In normal Wave cycle operation: never.
