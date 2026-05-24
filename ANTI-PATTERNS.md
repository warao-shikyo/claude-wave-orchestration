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

**Workaround we used**: Created "integration branches" like `plan/999b` that cherry-picked from prior `plan/<id>` branches. This worked but was reactive.

**Recommendation**: Add a between-Wave step to your method: integrate results to `main`, then proceed.

## 2. `_progress.md` merge conflicts everywhere

**What happened**: Sessions were instructed to "update your own row" in `_progress.md`. They edited it in their worktree, committed it, and pushed. When we later tried to think about merging all branches to `main`, **81 of them had touched `_progress.md`**.

**Why it's bad**: `_progress.md` is operational state, not source code. It should never have been in any branch's commit.

**Fix midway through the operation**: We started treating the orchestrator's `_progress.md` as the only canonical copy. Worktree copies became read-only snapshots that sessions could reference but not really merge.

**Recommendation from day 1**:
- Put `_progress.md` (and any operational state files) in `.gitignore` from the start
- OR keep `_progress.md` outside the repo entirely (e.g. in `~/.claude/`)
- Either way, ensure sessions don't try to commit their copy

## 3. PR/push policy was only formalized at Wave 9

**What happened**: For Waves 1-8, each session decided independently whether to make a PR and whether to push. Many summaries ended with "PR? push? what do you want me to do?" — the orchestrator had to make case-by-case decisions, and they weren't always consistent.

**Concrete failure modes**:
- Plan 604 ended up not pushed at all (local commit only), creating a recovery risk
- Plan 412's "PR or not?" was a 3-message back-and-forth
- Some chore plans got PRs (clutter), some new-feature plans didn't (lost visibility)

**Fix**: Wave 9 introduced an explicit policy table. The table is now in [METHODOLOGY.md §6](METHODOLOGY.md#6-prpush-policy).

**Recommendation**: Define your push/PR policy on Day 1 of the operation. Put it in your starter prompt template. Refer to it every Wave.

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

## 10. "Comprehensive testing" was deferred without a date

**What happened**: Almost every session ended with "real E2E testing is out of scope; that's for a separate test phase." After 122 plans, we had no test phase scheduled and a massive testing backlog.

**Why it happened**: Velocity was prioritized. Each session had to ship, not test. Reasonable choice — but the bill comes due.

**Recommendation**:
- Schedule the comprehensive test phase as part of the operation plan from Day 1
- Or: explicitly accept that velocity = test debt, and budget for the test phase after
- Or: alternate "build Waves" with "test Waves" to keep the debt manageable

## 11. We didn't establish "what's the production reality" baseline

**What happened**: Many "implicit done" verdicts read like: "the implementation looks done in code; can't tell if it works." We discovered later that things which looked done weren't actually deployed.

**Recommendation**:
- Before starting the operation, capture the deployment state baseline
- Note: which branches/commits are actually live in production
- Sessions should distinguish "code present in branch" vs "running in production"

## 12. We didn't have a `STOP` signal

**What happened**: The user could pause the operation by not approving the next Wave, but there was no clear "halt all sessions" mechanism. If a critical issue emerged mid-Wave, sessions kept working.

**Recommendation**:
- Define a SHUTDOWN signal — e.g. user adds `STOP` line to `_progress.md`
- Sessions should check for it before major actions
- Or just accept that "halt" = "close terminals" and document that fact

## 13. Cost wasn't tracked per session

**What happened**: We don't know the per-session token cost. We know the operation was expensive but not which sessions were the expensive ones.

**Recommendation**:
- If cost matters, instrument the launcher to log session start/end + use Claude Code's usage reports
- For optimization, batch sessions are remarkably cheap per outcome — favor them where possible

## 14. We didn't audit memory updates

**What happened**: Sessions sometimes wrote to long-term memory (e.g. project memory files). Some updates were great, some were ad-hoc. No one reviewed.

**Recommendation**:
- Include memory hygiene in the post-operation review
- Either accept memory as session-by-session contribution, or have a "memory editor" session post-operation

## 15. We never used CronCreate or scheduled work

**What happened**: This is more "what we didn't try" than "what went wrong." All sessions were synchronous to user activity.

**Possible enhancement**: A "harvest" cron that runs nightly and updates `_progress.md` with branch state changes, makes the next Wave's planning easier.

We didn't try it because the operation only ran 5 days. For longer operations it might be worth exploring.

## TL;DR

Top 3 things to fix on Day 1 of any future engagement:

1. **Merge to `main` between Waves**, don't let branches pile up
2. **Keep `_progress.md` out of all `plan/<id>` branches** — orchestrator-only state
3. **Establish PR/push policy and starter-prompt format upfront**, not at Wave 9
