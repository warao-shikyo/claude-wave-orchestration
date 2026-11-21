# Anti-patterns

Things we did wrong, things we'd do differently, things to avoid if you try this method.

## 1. Worktrees were created from stale `origin/main`

**What happened**: Every Wave's worktrees were created with `git worktree add -b plan/<id> origin/main`. But Waves 5-10 of work piled onto `plan/<id>` branches without ever merging back to `main`. So a Wave 9 session's worktree saw a `main` from before Wave 1, missing everything in between.

**Concrete failure modes**:
- Plan 415a's interaction-test session discovered 18 test failures from `select+exec_func` migration. Those were already fixed in `plan/415`, but `plan/415a` couldn't see them.
- Plan 412's session re-discovered a "fallback bug" that had already been fixed by `plan/402a` two days earlier (and itself was already in `main`).
- Several "is the test still failing?" investigations were repeated needlessly.

**What we should have done**:
- After each Wave, merge the wave's results back to `main` (or to a known-good integration branch) **before** starting the next Wave.
- Or: rebase each new worktree's branch on a designated "latest known good" branch instead of `origin/main`.

**Workaround we used**: Created "integration branches" like `plan/meta-002` that cherry-picked from prior `plan/<id>` branches. This worked but was reactive.

**Recommendation**: Add a between-Wave step to your method: integrate results to `main`, then proceed.

**v2 status**: standardized — [between-Wave integration](patterns/main-merge-strategy.md#between-wave-integration-during-the-operation) is now METHODOLOGY §4 step 6.5, and worktrees base off `integration/latest-known-good`.

## 2. `_progress.md` merge conflicts everywhere

**What happened**: Sessions were instructed to "update your own row" in `_progress.md`. They edited it in their worktree, committed it, and pushed. When we later tried to think about merging all branches to `main`, **81 of them had touched `_progress.md`**.

**Why it's bad**: `_progress.md` is operational state, not source code. It should never have been in any branch's commit.

**Fix midway through the operation**: We started treating the orchestrator's `_progress.md` as the only canonical copy. Worktree copies became read-only snapshots that sessions could reference but not really merge.

**Recommendation from day 1**:
- Exactly one writer: `_progress.md` lives on main and only the orchestrator commits it (one commit per patrol)
- Worktrees receive it through `git worktree add` as a read-only snapshot; sessions only stamp their own row
- Sessions report through an append-only `inbox.md` instead of editing shared state
- When merging a plan branch, keep main's `_progress.md`; union only append-only files like `inbox.md`
- (Alternatives if your setup prefers: `.gitignore` it, or keep it outside the repo)

## 3. PR/push policy was only formalized at Wave 9

**What happened**: For Waves 1-8, each session decided independently whether to make a PR and whether to push. Many summaries ended with "PR? push? what do you want me to do?" — the orchestrator had to make case-by-case decisions, and they weren't always consistent.

**Concrete failure modes**:
- Plan 604 ended up not pushed at all (local commit only), creating a recovery risk
- Plan 412's "PR or not?" was a 3-message back-and-forth
- Some chore plans got PRs (clutter), some new-feature plans didn't (lost visibility)

**Fix**: Wave 9 introduced an explicit policy table.

**Recommendation**: Don't make push/PR a per-session decision at all. The cleaner rule (now baked into the method) is that **a session master's landing authority ends at `commit`** — push, PR, and merge to main are all the user's call. No table to negotiate; sessions just commit.

**v2 status**: standardized — the landing model is now [METHODOLOGY.md §6](METHODOLOGY.md#6-landing-model): masters commit only; merge and deploy are the orchestrator's steps with user approval; push / PR are the user's. The earlier exception "masters may deploy from the worktree for verification" was withdrawn (see #20).

## 4. Topic drift on "remembered" plans

**What happened**: Plan 761 was originally tracked in the orchestrator's memory as "OAuth tokens encryption migration." But when the 761 session actually started, it executed a completely different scope (browser_tool improvements). Both got done, but neither matched the plan ID's original intent.

**Why**: The session that "remembered" the plan ID 761 was different from the session that had originally created the entry, and they had drifted on what 761 meant.

**Fix midway**: We created `plan/761b` to handle the actually-intended scope.

**Recommendation**:
- Lock the scope at plan-MD creation time, not at session-launch time
- Before launching a Wave, do a quick pass: do the plan MDs say what the orchestrator thinks they say?
- For plans that have been pending a while, re-read them before scheduling them in a Wave

## 5. We tracked sessions by completion summary only

**What happened**: We had no way to see live session state. The user had to paste the completion summary, or we had no idea what a session was doing.

**Concrete issue**: When a session got stuck waiting for user input, the orchestrator didn't know. We sometimes started a new Wave thinking the previous one was finished when 1-2 sessions were still mid-conversation.

**Workaround**: User maintained a mental model of which sessions were active. Worked because there were ≤10 in flight, but won't scale.

**Recommendation**:
- Have sessions write timestamps to a known location (e.g. update their row's `last_activity` field)
- Or: orchestrator can spot-check with `git log --all --since=1h` to see which branches have recent commits
- Or: instrument the launcher to log session PIDs and periodically check liveness

**v2 status**: standardized — see [session-monitoring.md](patterns/session-monitoring.md): the orchestrator wakes on masters' idle notifications (60-min fallback), judges liveness from commits and worktree changes, and a hook-maintained "waiting for the user" board tells the user which tab needs them.

## 6. We didn't establish "operational state vs project state" early

**What happened**: We mixed orchestration metadata (`_progress.md`, plan MDs) with the project itself (under `.claude/plans/` in the project's git tree). This caused:
- Plan MDs got committed to feature branches
- `_progress.md` got committed everywhere (see anti-pattern #2)
- Branch listings had `plan/<id>` mixed with feature branches

**Recommendation**: Strongly consider keeping operational state **out of the project repo**:
- `~/.claude/projects/<project>/plans/` for plan MDs
- `~/.claude/projects/<project>/_progress.md` for the dashboard
- Only commit final docs (e.g. INDEX.md, comprehensive_test_plan.md) to the project repo

The templates in this repo are designed to support either layout — see [templates/INSTRUCTIONS.md](templates/INSTRUCTIONS.md).

**v2 status**: we kept plans in the repo (`.claude/plans/`) but made the boundaries strict: `.claude/plans/` holds only plans not yet done (done ones are `git mv`ed to `docs/specs/` as an archive), `_progress.md` has a single writer, reports go to an append-only inbox, verify results go to `.claude/verify/`.

## 7. `.claude.json` lock contention on rapid launch

**What happened**: At one point we tried launching sessions 5 seconds apart. On one launch, the launcher hit `PermissionError: [Errno 13] Permission denied: '~/.claude.json'` because another launcher was still writing it.

**Why**: Multiple `launch_claude.py` instances all want to register the new worktree path in `~/.claude.json` (trust info).

**Workaround**: Wait 8 seconds and retry. Worked.

**Recommendation**:
- Stagger launches by at least 6 seconds
- Make the launcher resilient to lock contention (retry with backoff)
- See the included [`scripts/launch_claude.py`](scripts/launch_claude.py) for one approach

## 8. We didn't size-check the prompt early enough

**What happened**: Some starter prompts grew to 300-500 chars with embedded context. Most worked, but a few sessions reported confusion early in their conversation, possibly because critical context was deprioritized by the time Claude started reading the actual plan MD.

**Recommendation**:
- Keep starter prompts to ~200 chars when possible
- Put long context in the plan MD or supplementary files
- The prompt should set the role and point at the plan MD, not BE the plan MD

## 9. The orchestrator drifted into doing work

**What happened**: Late in the operation, the orchestrator started writing plan MDs directly (instead of having a session create them), drafting follow-up tickets, etc. This was efficient but blurred the role.

**Why it matters**: The orchestrator's only superpower is "knows everything." If it starts writing implementation, it competes with sessions, gets opinions, loses neutrality.

**Recommendation**:
- For new plan MD creation: spawn a tiny "scribe" session, don't write it in the orchestrator
- For decisions: refuse to decide, ask the user
- For implementation: never, period

In practice we still drifted. Discipline is hard. Acknowledge it and move on if it happens — but try.

**v2 follow-up — the "consultant" drift**: a later operation drifted the other way: the user started asking the orchestrator for comparisons, cost research, test proposals and "what should we do?", and the orchestrator answered (spawning research subagents, drafting plans). The patrol loop slipped and several execution requests from sessions sat unnoticed. The user's diagnosis: *"once you proposed the tests and I started relying on you for that, it broke."* Rule now: questions of the form compare / research / propose / "how should we" go to a **planner** session (write the gist to the inbox, reply in one line "handed to the planner"). The orchestrator only does launching, integration, deploy, pre-production checks, and running sessions' execution requests (#17). The same goes for raw problems: the orchestrator doesn't read a single file to "take a quick look" — it launches a planner session, which talks with the user and files `ready` plans.

## 10. "Comprehensive testing" was deferred without a date

**What happened**: Almost every session ended with "real E2E testing is out of scope; that's for a separate test phase." After 122 plans, we had no test phase scheduled and a massive testing backlog.

**Why it happened**: Velocity was prioritized. Each session had to ship, not test. Reasonable choice — but the bill comes due.

**Recommendation**:
- Schedule the comprehensive test phase as part of the operation plan from Day 1
- Or: explicitly accept that velocity = test debt, and budget for the test phase after
- Or: alternate "build Waves" with "test Waves" to keep the debt manageable

**v2 status**: standardized — see [test-waves.md](patterns/test-waves.md) (a test Wave every ~3 build Waves; each plan's DoD states how it was verified).

## 11. We didn't establish "what's the production reality" baseline

**What happened**: Many "implicit done" verdicts read like: "the implementation looks done in code; can't tell if it works." We discovered later that things which looked done weren't actually deployed.

**Recommendation**:
- Before starting the operation, capture the deployment state baseline
- Note: which branches/commits are actually live in production
- Sessions should distinguish "code present in branch" vs "running in production"

**v2 status**: standardized — the deployment baseline is METHODOLOGY §0. Only the orchestrator deploys; each deploy is recorded as `deploy: <date> main@<sha> <measured>` and followed by a verify, so `merged`, `deployed` and `verified` are distinct states. See [progress-template.md](templates/progress-template.md).

## 12. We didn't have a `STOP` signal

**What happened**: The user could pause the operation by not approving the next Wave, but there was no clear "halt all sessions" mechanism. If a critical issue emerged mid-Wave, sessions kept working.

**Recommendation**:
- Define a SHUTDOWN signal — e.g. user adds `STOP` line to `_progress.md`
- Sessions should check for it before major actions
- Or just accept that "halt" = "close terminals" and document that fact

**v2 note**: to stop paid batch work, stop *starting* the remaining items rather than killing processes. When a session process must be stopped, re-check its command line right before (PIDs are reused, #19), and never stop one that has uncommitted work.

## 13. Cost wasn't tracked per session

**What happened**: We don't know the per-session token cost. We know the operation was expensive but not which sessions were the expensive ones.

**Recommendation**:
- If cost matters, instrument the launcher to log session start/end + use Claude Code's usage reports
- For optimization, batch sessions are remarkably cheap per outcome — favor them where possible

**v2 status**: partially addressed — the launcher writes a per-launch record (tab name, role, plan id) to `~/.claude/wave-launch-log.jsonl`; join it against Claude Code usage reports. Usage limits also drove the token rules in [METHODOLOGY §11](METHODOLOGY.md#11-cost-considerations) (medium effort for the orchestrator, notification-driven wakes, one log line per checkpoint).

## 14. We didn't audit memory updates

**What happened**: Sessions sometimes wrote to long-term memory (e.g. project memory files). Some updates were great, some were ad-hoc. No one reviewed.

**Recommendation**:
- Include memory hygiene in the post-operation review
- Either accept memory as session-by-session contribution, or have a "memory editor" session post-operation

**v2 status**: auto memory is shared by every worktree of the same repo, so there is nothing to "collect" from worktrees. Masters write at most 2 durable, non-obvious facts directly (checking `MEMORY.md` for duplicates) and list them as `memory-written`; anything they're unsure about goes to `memory-candidates`, which the orchestrator files into the backlog for the user to decide.

## 15. We never used CronCreate or scheduled work

**What happened**: This is more "what we didn't try" than "what went wrong." All sessions were synchronous to user activity.

**Possible enhancement**: A "harvest" cron that runs nightly and updates `_progress.md` with branch state changes, makes the next Wave's planning easier.

We didn't try it because the operation only ran 5 days. For longer operations it might be worth exploring.

**v2 status**: the orchestrator now runs under `/loop` with `ScheduleWakeup` (idle notifications + a 60-min fallback), and the full test suite runs on a schedule once a day instead of in sessions or per deploy; the orchestrator files the morning's failures as fix plans.

## 16. Verbose completion summaries inflated the orchestrator's context

**What happened**: Sessions sent rich completion summaries (300-1500 chars each) to the user, who pasted them to the orchestrator. The orchestrator's context bloated faster than necessary — we burned through compaction cycles every ~30-40 summaries on a heavy day.

**Why it matters**: The orchestrator only needs **enough to update one row** in `_progress.md`. Everything else is in the session's plan MD and its commits on the local `plan/<id>` branch. The detailed prose, while pleasant to read, was duplicating context the orchestrator didn't need to retain.

**Concrete numbers** (rough estimate for the ~120-plan operation):

| Approach | Context per summary | Total for 120 summaries |
|---|---|---|
| Verbose summary (what we did) | ~3-5 KB | ~500 KB |
| Verbose summary + orchestrator re-reads `_progress.md` | ~15 KB | ~1.5 MB |
| Minimal summary + orchestrator uses `Edit` only | ~500 chars | ~60 KB |

The orchestrator at peak was running well below its compaction limit but unnecessarily close to it. A heavier operation (300+ summaries) would have triggered compaction repeatedly.

**Fix in this method going forward**: Two complementary tactics.

### Tactic A: orchestrator avoids re-reading `_progress.md`

The orchestrator should update `_progress.md` via the `Edit` tool's diff-only mechanism, not by reading the file each time and rewriting. This requires:

- Reading `_progress.md` **once** at orchestrator startup (so the tool can target it)
- After that, every update is `Edit(old_string=<one row>, new_string=<one row>)`
- Re-reading is only necessary when the user asks for an explicit dashboard view

This alone saves ~10 KB per summary.

### Tactic B: separate the two audiences — and take the user out of the relay

We initially thought short summaries were strictly better. **They're not** — the user actually values rich summaries for their own situational awareness. The right move is to **separate the two audiences**. We first did this by having sessions print two sections and the user paste the short one to the orchestrator. That still made the user a relay. Now:

- **For the orchestrator**: the session appends a short structured report (≤12 lines) to `.claude/plans/inbox.md` and **commits** it. The orchestrator reads the inbox on its patrol — nobody pastes anything.
- **For the user**: the session prints a detailed summary in its own terminal, and writes the full report in the plan MD.

```
## [<id>] <HH:MM> done|cancelled|blocked
commit: <hash> (push: no — commit is the end of responsibility)
verified: unit|integration|manual|deferred
deploy: none
verify: <what to check after deploy, or none>
done-file: <id>-<slug>_done.md
updated-docs / new-issues / residual: <0-3 lines each>
memory-written / memory-candidates: <file names / facts, or none>
key: <30-chars take-away>
```

### Combined effect

With both tactics, orchestrator context per summary drops from ~15 KB to ~500 chars — a **30x reduction** — and the user no longer spends attention copying text between tabs.

### Instructions for the human (user)

1. **Read the detailed summary in the session's tab yourself** — that's where situational awareness lives.
2. **Don't paste summaries into the orchestrator.** Paste only when a cross-session message didn't arrive, and then only its plain body (see #18).
3. If you want the orchestrator to track a cross-cutting issue from a detailed summary, **say so explicitly**.
4. **Do ask the orchestrator "what should be in the next Wave?" / "merge now?"** — high-value orchestrator reasoning. Don't ask it to research or compare (that's a planner's job, #9).

## 17. Sessions couldn't run privileged commands, and their requests got lost

**What happened**: Sessions ran in a restricted permission mode, so reading production data, using API keys and calling paid external APIs were denied. The orchestrator (running with broader permissions) ended up running those commands for them via a subagent — but this was never written down as a procedure. Requests were scattered across the plan branch's inbox, the main inbox, and uncommitted inbox edits in worktrees, and some were missed for hours. One request claimed "user approved" without saying where.

**Recommendation**:
- Make "execution requests" a formal channel: the session appends `## [<id> → orchestrator] execution request` to the inbox with the exact command, count, cost estimate, output location (e.g. the worktree's git-ignored `out/`), and where the user approved it — and commits it.
- The orchestrator checks **all three places** every patrol: each plan branch's inbox, the main inbox, and each worktree's uncommitted inbox diff. Also pick up every branch's `mark done` commit on each patrol, not only the ones that sent a notification.
- "User approved" must name the chat and time; if it can't be confirmed, ask the user before spending money or touching production. Writes to production stay behind the dry-run → approval gate.
- Put the list of denied operations and the request format into each session's starter context, so sessions ask instead of improvising workarounds.

## 18. Cross-session messages silently expired

**What happened**: The orchestrator sent messages to sessions with cross-session messaging. Because the two sides ran in different permission modes, each message waited for approval on the receiving side and expired unseen; the sender saw success. When the user copy-pasted a message into the other session with its wrapper tags intact, it was dropped as well.

**Recommendation**:
- Treat direct messages as a "wake up" hint only. The content of record goes into the inbox **and is committed**.
- The only reliable paths are: inbox commit, or the user pasting the plain body text (without wrapper tags).

## 19. Small operational traps around cost, integration and tests

- **Killing by PID number alone**: a PID recorded earlier had been reused by an unrelated process; it was nearly killed. Stop budget overruns by not starting the remaining work; when you must stop a running process, re-check its command line right before killing it.
- **Merging during a deploy**: if the deploy uploads the local working tree, merging into main mid-deploy ships a half-integrated state. Wait for the deploy to finish.
- **Shared version numbers collided**: two plans each bumped the same shared template version N→N+1. Picking one side silently drops the other. Combine both and bump to a new version.
- **A test run that ran nothing**: passing non-test files or nonexistent paths to the test wrapper ended "successfully" with zero tests. Always read the passed count.

## 20. Masters deployed "for verification" from their worktrees

**What happened**: Sessions were allowed to deploy from their worktree to verify their own work. Many deploy commands sync the **working tree**, not a git ref — so a deploy from `plan/<id>` would have shipped production without every other session's work that wasn't in that branch. It was caught just before it happened. Meanwhile other masters, unable to deploy, sat `blocked` "waiting for deploy", holding worktrees and tabs open.

**Recommendation**:
- Masters never deploy. Post-deploy checks go into the inbox `verify:` line (command, value to look at, expected value) and the master declares done.
- One deployer: the orchestrator integrates into main, deploys main with user approval, measures the result (content hash, not only the revision number), and runs verify once per deploy.
- A verify failure doesn't reopen the plan: a planner files a fix plan.

## 21. The plan MD never reached the worktree, and seeding broke tracked files

**What happened**:
- A plan MD written into the root's `.claude/plans/` but not committed to the base branch is invisible in a new worktree — `git worktree add` only brings committed files. A session started without its plan.
- Copying `_progress.md` / `inbox.md` / `INSTRUCTIONS.md` from the root into the worktree overwrote the base's newer versions with whatever branch the root happened to be on, leaving "rolled back" uncommitted changes. Emptying `inbox.md` in a worktree, once committed, would have deleted other sessions' reports.
- A STARTER.md generated for another plan was left in place, and the session read the wrong mission.

**Recommendation**: seed by `cp` **only** the files the base lacks (the plan MD, the generated STARTER.md), and run a pre-launch check that refuses to launch unless the plan MD exists in the worktree, STARTER.md names this plan, and no tracked file is modified.

## 22. Git Bash ate the slash command

**What happened**: Launching `python launch_claude.py <path> "/session-master auth-001 ..."` from Git Bash turned the prompt into `C:/Program Files/Git/session-master auth-001 ...` (MSYS path conversion). The session started but the slash command never ran.

**Recommendation**: always prefix with `MSYS_NO_PATHCONV=1`, and pass absolute paths in `C:/...` form (`$(pwd -W)`), since `/c/...` is no longer converted. Verify once by looking at the launched process's command line. Also: no backticks in launch prompts — bash executes them.

## 23. Parallel test runs froze the user's machine

**What happened**: Every master ran the test suite on its own schedule, several at once. CPU and IO saturated and the user's terminal became unusable.

**Recommendation**:
- Only one test run at a time across all sessions — an exclusive wrapper that queues, with the raw test command blocked by a hook.
- Sessions run only the suites covering what they touched, once, before completion; never the full suite.
- The full suite runs on a schedule once a day; not per session, not per deploy.
- Limit concurrent masters (3-6).
- Read the passed count: a wrapper given non-test files can "pass" with zero tests (#19).

## 24. Inventory and liveness judged from the wrong signals

**What happened**:
- A plan looked "not started" for weeks because its file in main's `.claude/plans/` still had the pre-done name — done happens on the branch, and main only sees it after merge.
- A master was judged dead because its conversation-log directory didn't exist yet; it had already made two commits.
- Sessions were judged in the first minute after launch, before their first response.
- A session-listing command returned nothing — not even the orchestrator itself — and was read as "no sessions to stop", so finished masters were never stopped.

**Recommendation**:
- Done = `chore(plan-<id>): mark done` in `main..plan/<id>` (limit the range — grepping the whole branch also matches main's old mark-done commits). Check this before putting a plan in a Wave; done-but-unmerged plans are integration work.
- Liveness = commits (`git rev-list --count plan/<id> ^main`) and worktree changes (`git status --porcelain`); wait a few minutes after launch.
- Ask the OS for processes. A list that doesn't even contain yourself is broken, not empty.

## 25. Worktree removal failed, and dead tabs piled up

**What happened**: On Windows a running session locks files in its worktree, so `git worktree remove` failed after done and the post-processing chain stalled while the user was away. The console session ignores a polite close, so it must be force-stopped — and a force-stopped tab stays open as "process exited with code 1" unless the terminal is told to close tabs on any exit.

**Recommendation**: post-processing stops the finished master first — only if its plan is done and its worktree has no uncommitted changes, matching the exact plan id on the command line and never touching the orchestrator or other plans — then removes the worktree (keeping the branch). Configure the terminal to close tabs on exit, or tell the user how many dead tabs to close. Also never launch a second master for a plan whose master is still running: two sessions in one worktree collide on commits.

## 26. The loop ended after the user asked a question

**What happened**: The orchestrator ran under `/loop` and re-armed itself with `ScheduleWakeup` at the end of each patrol. Whenever the user stepped in with a question, it answered and ended the turn — without booking the next wake. `/loop` dynamic mode only continues through that call, so the orchestrator sat idle for hours while masters finished and waited.

**Recommendation**: every orchestrator turn ends with `ScheduleWakeup`, replies to the user included; stopping on purpose is written out with a fixed marker. Back the rule with a `Stop` hook that blocks once when an orchestrator session has no booked wake and no marker (see [session-monitoring](patterns/session-monitoring.md#re-arm-after-answering-the-user)).

---

## TL;DR

Top things to fix on Day 1 of any future engagement:

1. **Integrate between Waves** into `integration/latest-known-good`, don't let branches pile up
2. **One writer for `_progress.md`** (the orchestrator, on main) — never merged from `plan/<area>-<NNN>` branches
3. **Masters commit only; the orchestrator alone merges and deploys** (with user approval), then verifies
4. **Reports go through a committed inbox, not the user's clipboard**; the orchestrator uses `Edit` for `_progress.md` and wakes on idle notifications
5. **One test run at a time, no full suite in sessions** — the full suite runs on a schedule
