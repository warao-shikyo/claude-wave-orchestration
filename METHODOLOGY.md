# Methodology

The full method, in depth. Read [README.md](README.md) first for the elevator pitch.

## 0. Kickoff: capture the baseline

Before launching Wave 1, make three decisions that are cheap upfront and expensive to retrofit (we retrofitted all three — ANTI-PATTERNS #1, #3, #11):

1. **Deployment baseline** — Record what is actually live in production now (commit/tag per environment). "Code in a branch" ≠ "running in production". Only the orchestrator deploys, and every deploy is recorded in [`_progress.md`](templates/progress-template.md) as `deploy: <date> main@<sha> <measured>`.
2. **Landing model** — Session masters carry plans to **commit only**; merge and deploy are the orchestrator's steps with user approval (see [§6](#6-landing-model)). This is fixed by the skill, but state it in STARTER.md so every session sees it.
3. **Integration target** — Decide where Wave results land between Waves (default: an `integration/latest-known-good` branch). See [§4 step 6.5](#4-wave-anatomy).
4. **Test schedule** — Sessions never run the full suite and never run tests concurrently. Set up a scheduled full-suite run (once a day, e.g. at night) before Wave 1.

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

Think of it as a **parallel pipeline**. Plans are written by a **planner**, executed by **session masters**, and coordinated by one **orchestrator**:

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
           │ inbox.md report + commit │
           ▼                          ▼
        (orchestrator picks it up on its next patrol:
         merge → deploy → verify, each step with user approval)
```

Upstream of this sits the **planner**: a session that takes a raw problem (bug, request, consultation), works it out with the user, and files plan MDs as `ready` in `.claude/plans/`. The orchestrator never investigates raw problems itself — it launches a planner.

Three properties make this work:

1. **Worktree isolation** — Each session works in its own `.worktrees/<area>-<NNN>/` directory on its own branch. They cannot step on each other.
2. **Single source of truth** — `_progress.md` lives in the orchestrator's working directory only. Worktree copies are read-only references.
3. **Direct user dialogue per session** — Main sessions talk to the user without going through the orchestrator. The orchestrator handles state, not conversation.
4. **File-based hand-offs** — planner → orchestrator is a `ready` plan MD; orchestrator → master is the seeded plan MD + STARTER.md; master → orchestrator is an appended, committed `inbox.md` report. Cross-session messages are only wake-up hints.

## 3. Roles in detail

### How sessions are started (launch types)

| Type | When | Tab name / color |
|---|---|---|
| **single** | Normal work in one project (the default) | `S:<project> <task>` grey |
| **planner** | No plan yet — a problem needs investigating and turning into plans | `P:<project> <task>` green |
| **orchestrator** | Plans already exist and many independent ones should run in parallel | `O:<project> <task>` purple |
| **master** | Launched by the orchestrator, one per plan | `M:<project>/<plan-id> <plan title>` blue |

Before launching, settle four things with the user: **purpose, completion criteria, scope, and what must not be touched** (a "kickoff"). Then pick the type and launch with [`launch_claude.py`](scripts/launch_claude.py) `--role <type> --task "<summary>"`. The tab name is also the Remote Control name and the `--name` used as a cross-session messaging address. Colors stand for the role, never the state. Use Opus for every role by default.

### Planner (one per problem, short-lived)

**Does:**
- Talks with the user to pin down scope, priority and acceptance criteria (a consultant, not a silent research bot)
- Delegates broad investigation to subagents and keeps only the conclusions
- Splits the problem into plans that one master can finish in one worktree; files them in `.claude/plans/` as `ready` (or `draft` if undecided)
- In **fix mode** (`/session-planner 改修: <verify result | board item | backlog line>`), files a new fix plan describing only the difference from the original plan
- Delivers extra specs for a running plan as `.claude/plans/addenda/<id>-<YYYYMMDD-HHMM>.md`

**Does NOT:** write feature code, launch sessions, create branches/worktrees, edit `_progress.md`, push / merge / deploy.

### Orchestrator (one session)

**Does:**
- Proposes each Wave and launches it after user approval
- Creates worktrees, seeds them (plan MD + STARTER.md), checks them (b3), launches masters with `launch_claude.py`
- Sleeps between patrols; wakes on masters' idle notifications (or a timer) and reads the **inbox** (reports, execution requests), `_done` files and commits
- Updates the master `_progress.md` (one commit per patrol) and files new-issues / residual / memory candidates into `_backlog.md`
- Post-processes done plans through a subagent (archive to `docs/specs/`, stop the master process, remove the worktree)
- With user approval: merges `plan/<id>` into main, deploys main, then runs verify
- Runs masters' execution requests (privileged commands) through a subagent
- Launches a planner for any raw problem, and for compare / research / "how should we" questions

**Does NOT:**
- Write feature code or plan MDs itself
- Investigate raw problems itself (even "just a quick look" — launch a planner)
- Commit to `plan/<id>` branches
- Relay the user's answers or judgments between sessions

The orchestrator is the **conductor**, not a performer.

### Main session / session master (one per plan, N parallel)

**Does:**
- Owns the plan it was launched with, from start to "done" or "cancelled"
- Talks to the user directly when needed
- **Commits** — that's the end of its landing authority (see [§6 landing model](#6-landing-model))
- Updates docs for its change, writes a full report into the plan MD, appends a short report to the inbox
- Marks done by **renaming its plan file to `<id>-<slug>_done.md`** as the very last commit
- Writes durable, non-obvious facts to auto memory (max 2), or lists them as `memory-candidates`
- Sometimes discovers the plan is already done — judges it "implicit done"
- Sometimes discovers the plan should be canceled — judges it "cancelled" with reasoning

**Does NOT:**
- Push, open PRs, merge to main, **or deploy** (post-deploy checks go into the inbox `verify:` line)
- Run the full test suite, or tests in parallel with other sessions
- Edit other sessions' worktrees
- Make decisions outside its plan's scope (escalates to user or notes as "out of scope")

### User

**Does:**
- Settles purpose / completion criteria / scope / no-go areas at kickoff
- Answers the questions each session asks in its own tab (the orchestrator only says *which* tab is waiting)
- Approves Waves, merges and deploys (the orchestrator asks once per batch)
- Decides on memory candidates and on whether filed backlog items become plans

**Does NOT need to:**
- Watch every session or paste summaries — reports flow through the inbox
- Make every decision (sessions decide cancelled vs done with reasoning)
- Manually track progress (`_progress.md` does that)

## 4. Wave anatomy

A "Wave" is **one cycle of: plan → launch → execute → summarize → integrate**.

```
Wave start
   │
   │ Orchestrator proposes 8-12 ready plans; the user approves
   │ (first: check each candidate's branch for `mark done` — done-but-unmerged
   │  plans are integration work, not Wave material)
   ▼
1. CREATE a worktree per plan (git worktree add, base = integration branch)
   │
   ▼
2. SEED: cp the plan MD only (the one file the base lacks) + generate STARTER.md
   (INSTRUCTIONS.md / _progress.md / inbox.md are tracked and arrive via worktree add)
   │
   ▼
2.5 CHECK (b3): plan MD present, STARTER.md is for this plan, no tracked file
   modified, no master for this plan still running — otherwise don't launch
   │
   ▼
3. LAUNCH masters with launch_claude.py, 5-6 sec apart, 3-6 running at once
   │
   ▼
4. SESSIONS WORK independently. The orchestrator subscribes to each master's
   idle notification and sleeps (ScheduleWakeup 60-min fallback; 20-30 min
   polling if notifications aren't available). It never busy-polls.
   │
   │   ┌───────────────────────────────────────────────┐
   │   │ Sessions ask the user directly in their tab;  │
   │   │ on completion they append a short report to   │
   │   │ inbox.md, commit, and rename the plan _done   │
   │   └───────────────────────────────────────────────┘
   ▼
5. ON WAKE the orchestrator reads inbox / _done / commits / waiting-user,
   updates _progress.md (Edit, one commit per patrol), files the backlog,
   and post-processes done plans through a subagent
   │
   ▼
6. WAVE DONE when all rows are done/cancelled/blocked
   │
   ▼
6.5 INTEGRATE (with user approval) — see below
   │
   ▼
6.7 DEPLOY + VERIFY (with user approval; orchestrator only) — see §6
   │
   ▼
7. PLAN NEXT WAVE (verify failures come back as fix plans from a planner;
   every ~3rd Wave can be a TEST Wave)

Wave end
```

### Orchestrator landing & follow-up rules

- **Always file new issues / residual work into the backlog.** Each inbox report's `new-issues`, `residual` and `memory-candidates` go into `.claude/plans/_backlog.md` (`Candidate plans`). Never swallow them.
- **Don't auto-spawn follow-up sessions.** When a backlog item is ready to become a plan, ask the user first (and let a planner write it).
- **Keep `.claude/plans/` to plans not yet done.** As part of post-processing, `git mv` each `<id>-<slug>_done.md` to `docs/specs/`. That folder is an archive, not reading material — the source of truth is the `mark done` commit.
- **Stop the master before removing its worktree.** On Windows a running session locks files. Check the worktree is clean (`git status --porcelain` empty) and keep the `plan/<id>` branch.
- **The orchestrator only commits** `_progress.md`, `_backlog.md`, and `docs/specs` archival on main — never feature code, never to `plan/<id>` branches.

### Step 6.5 in detail — between-Wave integration

Letting `plan/<id>` branches pile up unmerged is the **#1 anti-pattern**: later Waves base off a stale `origin/main` and re-discover already-fixed bugs. So after each Wave:

1. Merge the Wave's `done` branches into `integration/latest-known-good`, resolving the small conflicts now (~10 branches) rather than later (~90)
2. Base the next Wave's worktrees on that branch

Merges are done by the orchestrator **with user approval** (asked once per batch). Union only append-only files such as `inbox.md`; never union STARTER.md, plan MDs or code. Don't merge while a deploy is running. Full mechanics in [main-merge-strategy.md](patterns/main-merge-strategy.md#between-wave-integration-during-the-operation).

### Wave sizing

We used Waves of **8-12** plans consistently, but run only **3-6 masters at the same time** (launch the rest as earlier ones finish). Rationale:

- **<8 plans**: orchestrator under-utilized; user could just run a single session
- **8-12 plans**: sweet spot — enough parallelism to feel fast, few enough to keep `_progress.md` mentally tractable
- **more than 3-6 running at once**: tests and CPU compete (parallel test runs made the user's machine unusable), `.claude.json` contention, usage limits drain fast, and the user is overwhelmed by simultaneous conversations

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

## State legend
- ready / implementing / done / merged / deployed / verified / verify-failed (+ cancelled / blocked)
- wake_mode: notify   (or poll)
- idle_cycles: 0      (consecutive no-change fallback wakes; 3 → wait for the user)

## Wave N (YYYY-MM-DD)

| ID | Title | wave | state | launched_at | branch | notes |
|---|---|---|---|---|---|---|
| auth-001 | Add feature X | 1 | merged | 2026-... | plan/auth-001 | commit abc123, postprocessed |
| billing-002 | Refactor Y | 1 | implementing | 2026-... | plan/billing-002 | blocked on plan-auth-001 |
...

## Execution log

YYYY-MM-DD
- HH:MM Wave 1 launched: auth-001, billing-002, ...
- HH:MM Wave 1 landed: 8 done, 1 cancelled, 1 blocked
```

### Update rules

1. **The orchestrator owns the master copy** on main and is its only writer — `Edit` diffs, one commit per patrol.
2. **Each worktree gets a read-only snapshot** through `git worktree add` (don't `cp` it in from the root — that can overwrite it with a stale version).
3. **Sessions only stamp their own row** (`last_activity`, `status: waiting-user`). Their real report goes to the inbox.
4. **The `state:` column is a note.** The facts are the `mark done` commit, `merge-base`, and the deploy / verify records. When they disagree, fix `state:`.
5. **Never merge `_progress.md` from a plan branch.** Keep main's version.

This is the single biggest gotcha. See [ANTI-PATTERNS.md](ANTI-PATTERNS.md).

## 6. Landing model

The original engagement let each session decide whether to push and open PRs, and it caused churn (ANTI-PATTERNS #3). Later, sessions deploying "for verification" from their worktrees nearly shipped production without other sessions' work. The model is now fixed:

> **A session master's landing authority ends at `commit` (and `mark done`).** Merge and deploy belong to the orchestrator, each with user approval. push / PR are the user's call.

| Action | Who |
|---|---|
| Implement + **commit** to `plan/<id>` | session master (on its own judgment) |
| Mark done = rename file to `<id>-<slug>_done.md` + commit (last) | session master |
| Write post-deploy checks as `verify:` in the inbox | session master |
| **merge** `plan/<id>` into main / the integration branch | orchestrator, with user approval |
| **deploy** main | orchestrator only, with user approval |
| **verify** after each deploy | orchestrator |
| **push** / **open a PR** | user |

Why masters never deploy: many deploys sync the **working tree** to production. A deploy from a worktree silently removes every other session's work that isn't in that branch, and the master can't know whether its branch contains the latest main.

Deploy invariants (the project's own deploy skill, if any, decides the commands; these always hold):

- Integrate into main first, then deploy main — never a plan branch.
- Never merge into main while a deploy runs; never run two deploys at once.
- Run the deploy through a subagent **synchronously** (a background command dies with the subagent).
- Production writes (`--apply`-style) need a dry-run shown to the user and approval.
- Respect order constraints the masters wrote down ("code first, config second").
- Measure the result yourself — revision **and** the content hash; a newer revision number can still carry old content.
- Record `deploy: <date> main@<sha> <measured>`, then verify.

**Verify** runs once per deploy and covers every plan in it: the project's verify skill if it has one, otherwise the plans' inbox `verify:` lines run by a read-only subagent. The result goes to `.claude/verify/<YYYYMMDD-HHMM>-<sha>.md`. On failure, the affected plans become `verify-failed` and a planner in fix mode files a new `ready` plan; the original plan is never reopened.

## 7. Patterns to use

These are detailed in [patterns/](patterns/) but here's the index:

- **[Wave strategy](patterns/wave-strategy.md)** — How to size, sequence, and content-mix Waves
- **[Batch sessions](patterns/batch-sessions.md)** — Consolidating 10+ trivial judgments into one session (the "999 family" pattern)
- **[Implicit done detection](patterns/implicit-done-detection.md)** — Verify rather than re-implement
- **[INDEX done pattern](patterns/index-done-pattern.md)** — Closing parent INDEX plans once children are settled
- **[Main merge strategy](patterns/main-merge-strategy.md)** — Resolving the 90-orphan-branches problem, plus between-Wave integration
- **[Test Waves](patterns/test-waves.md)** — Interleaving verification Waves so test debt stays bounded
- **[Session monitoring](patterns/session-monitoring.md)** — Idle notifications, liveness from commits, the waiting-user board

## 8. Lifecycle of a typical plan

```
draft → ready → implementing → done → merged → deployed → verified
          ▲                                         │ problem found
          └── planner (fix mode) files a fix plan ◀─┘   original plan → verify-failed

side detours inside implementing:
  → blocked (record reason; orchestrator may reassign or wait)
  → waiting-user (session asks the user in its own tab)
  → "implicit done" verdict (no code change, just _done rename + audit trail)
  → INDEX consolidation (close once children are done)
  → cancelled (Status + reason; no rename)
```

| Transition | Who | Approval |
|---|---|---|
| → `ready` | planner | — (`ready` means "OK to launch") |
| `ready` → `implementing` | orchestrator | **user** (new Wave / next plan) |
| `implementing` → `done` | master | — (mark-done commit + inbox report) |
| `done` → `merged` | orchestrator | **user** |
| `merged` → `deployed` | orchestrator | **user** |
| `deployed` → `verified` / `verify-failed` | orchestrator | — (read-only checks) |
| `verify-failed` → fix plan `ready` | planner (fix mode) | — |

`done` is expressed by renaming the plan file to `<id>-<slug>_done.md` and committing `chore(plan-<id>): mark done`; it is terminal — never renamed back or relaunched. On each wake the orchestrator advances only the plans whose state changed, by one step, and asks for approvals once per batch.

## 9. When does the operation end?

When `_progress.md` shows zero rows that are still `draft`, `ready`, or `implementing`, and every done plan is merged, deployed and verified (or explicitly parked). Everything is `done`, `cancelled`, or `blocked` with a clear external dependency.

You can also declare "phase complete" at any natural stopping point — the method is not all-or-nothing.

## 10. After the operation

Things that need to happen after the last Wave:

1. **Leftover merges** — If you merged as you went ([§4 step 6.5](#4-wave-anatomy), [§8](#8-lifecycle-of-a-typical-plan)), only stragglers remain. Otherwise see [main-merge-strategy.md](patterns/main-merge-strategy.md).
2. **Test confirmation** — With the scheduled full suite and [test Waves](patterns/test-waves.md), this is *confirmation*, not *discovery*. If you deferred all testing, schedule the all-at-once QA phase explicitly.
3. **Final deploy + verify** — Bring the deployment baseline (§0) in line with reality.
4. **Memory / knowledge consolidation** — Decide the backlog's "memory candidate" items; move durable, non-obvious decisions into the project's knowledge docs (not what the code already says).

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
{"ts": "...", "event": "launch", "project_path": "...", "tab_name": "M:myapp/auth-001 ...", "role": "master", "plan_id": "auth-001", "mode": "wt"}
```

To reconcile cost:

1. Each line gives a session's start time and plan id
2. Join against Claude Code's own usage report for the same window
3. Attribute tokens to plan ids by launch time

Use this to confirm what we observed by feel: **batch and audit sessions are remarkably cheap per outcome** (often 1/10th of an implementation session). Favor them where the work allows — see [batch-sessions.md](patterns/batch-sessions.md) and [implicit-done-detection.md](patterns/implicit-done-detection.md).

In our case, the 5-day operation closed ~120 plans. The token cost was significant but well below the value delivered.

Later operations hit weekly usage limits, which led to these rules:

- Run the orchestrator at `--effort medium`; most patrols are "nothing changed". Raise effort (or say `ultrathink`) only for turns needing deep judgment.
- Wake on idle notifications with a 60-min fallback rather than frequent polling.
- Masters log one line per checkpoint, keep the inbox report ≤12 lines, read only the plan / STARTER / the files they touch, and run their tests once before completion.
- Use Opus by default for every role; use another model only when the user names one. A subagent still spends tokens — it protects the parent's context, not the budget. Use one for broad searches; look directly when you know where to look.
- When a batch of paid work threatens to exceed a budget, stop by not starting the remaining items; before killing a running process, re-check its command line (PIDs get reused).

## 12. Context economy (orchestrator side)

The orchestrator session runs the longest of any session — typically days. Without discipline, its context window fills with summaries, file reads, and acknowledgments faster than you'd expect.

### What inflates the orchestrator's context

- **Re-reading `_progress.md`** for each update (~10 KB per Read)
- **Verbose completion summaries** (~3-5 KB each, ~500 KB for 120 plans) — the original engagement had the user paste them
- **Long acknowledgments** by the orchestrator (~500 chars-1 KB each)
- **Grep / Glob / Bash output** when checking branch state

### What keeps it lean

| Tactic | How much it saves (per summary cycle) |
|---|---|
| Use `Edit` (diff-only) instead of `Read + Write` for `_progress.md` | ~10 KB |
| Short structured inbox reports from sessions instead of prose | ~3 KB |
| Acknowledge in ≤2 sentences | ~500 chars |
| Avoid spot-checks (`grep`, `git log`) unless the user asks | ~200-500 chars |
| Use Claude Code's prompt cache (default; no action needed) | API cost only, not context |

### Specific instructions for the orchestrator

These should be in your bootstrap prompt (see [`templates/orchestrator-bootstrap-prompt.md`](templates/orchestrator-bootstrap-prompt.md)):

1. **Read `_progress.md` once at startup**, then use `Edit` for every subsequent update
2. **Acknowledge completion summaries in ≤2 sentences**: status updated + 1 cross-cutting observation if any
3. **Don't re-Read files** unless the session's last edit was 30+ minutes ago (assume your "remembered state" is current)
4. **Don't grep/glob unless asked** — the routine exception is the wake check (inbox, `_done` files, recent `plan-` commits — see [§4](#4-wave-anatomy))
5. **Batch** — handle several notifications in one turn, post-process several done plans with one subagent, commit `_progress.md` once per patrol
6. **Hand off post-processing** (archive, backlog filing, worktree removal) to a subagent; don't read plan_done bodies or docs yourself

### Specific instructions for sessions

These live in STARTER.md (see [`templates/starter-md-template.md`](templates/starter-md-template.md)) and INSTRUCTIONS.md:

On completion, sessions write to **two places for two audiences**:

- **For the orchestrator** — append a short structured report to `.claude/plans/inbox.md` and commit it (format in [INSTRUCTIONS.md](templates/INSTRUCTIONS.md#inbox-short-report-append-to-claudeplansinboxmd)): status, commit, `deploy: none`, `verify:`, done-file, new-issues, residual, memory-written / memory-candidates, a 30-char key. ≤12 lines.
- **For the user** — a detailed summary printed in the session's own terminal (what changed, verification, test/build highlights, discoveries). The user reads it whenever they like; it never enters the orchestrator's context.

Detailed prose also lives in the plan MD (full report + execution log) and commit messages. The `new-issues` / `residual` / `memory-candidates` fields are mandatory raw material — the orchestrator files them into the backlog.

### Specific instructions for the human (user)

1. **Read the detailed summaries in the session tabs yourself** — that's where situational awareness lives.
2. **Don't paste summaries to the orchestrator** — it reads the inbox. Paste text only when a cross-session message failed to arrive, and then only the plain body (without wrapper tags).
3. **If you want the orchestrator to track a cross-cutting issue**, say so explicitly.
4. **Don't ask the orchestrator for comparisons, research or "how should we…"** — that pulls it into consulting and it misses its patrol. Ask a planner.
5. **Do ask the orchestrator high-leverage questions**: "what's next?", "is this ready for a Wave?", "merge / deploy now?".

### Why this matters at scale

For a 500-plan operation:

| Discipline | Cumulative orchestrator context |
|---|---|
| No discipline (re-Read + verbose summaries) | ~7.5 MB before compaction |
| Verbose summaries + Edit only | ~2.5 MB |
| Short inbox reports + Edit only | ~250 KB |
| Short inbox reports + Edit + batching | ~150 KB |

The difference between "no discipline" and "full discipline" is ~50x. A long operation that **never hits compaction** stays fast, coherent, and cheap. One that compacts repeatedly loses fidelity in the orchestrator's mental model — you'll feel it as "wait, what was plan 412 about again?"

### When the orchestrator *should* read full files

- **Operation startup**: read `_progress.md` once to load state
- **After a multi-hour break**: re-read to refresh
- **When the user asks "what's the current state?"**: a fresh read avoids stale snapshots
- **When debugging an Edit failure**: re-read to find the exact `old_string`

In normal Wave cycle operation: never.
