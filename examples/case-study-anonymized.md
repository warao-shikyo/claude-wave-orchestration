# Case study: clearing a ~120-plan backlog in 5 days

Anonymized walkthrough of the engagement that produced this method.

## Project profile

- Multi-tenant SaaS, Python / Flask / Cloud Run
- ~6 months of accumulated plan files (~140 in total, ~120 actionable)
- Backlog spanned: feature work, refactors, AI integrations, browser-automation extensions, billing, customer onboarding flows
- Single human user driving development (with one paying customer pending)
- Started as: "the plans folder is out of control, let's clean it up"

## Day 0 — Recognition

The user had been doing single-session Claude Code work for months. Productivity was good but the plans folder kept growing — by Day 0 it had ~140 files in `.claude/plans/`, many in `draft` or `ready`, never closed.

The user's question: **"Can we parallelize?"**

Initial answer: Yes, with discipline. Method designed in conversation that day.

Key initial decisions:
- 10 sessions per "Wave"
- Worktree per session
- One orchestrator session manages `_progress.md`
- Sessions talk to user directly (no orchestrator middleman)

## Day 1 — Wave 1 (12 sessions)

Launched 12 sessions for the highest-impact plans, all from one user-facing feature group.

**Immediate problem**: Worktrees were created from `origin/main`, which didn't have the plan MDs yet (they were uncommitted local files). Sessions launched with no context.

**Recovery**: User closed all 12 terminals. The orchestrator:
1. Added the plan MDs to `.gitignore`-aware copies in each worktree
2. Re-launched sequentially, 5 sec apart

This recovery cost an hour but established a discipline: **seed worktrees with plan MDs before launching**.

**Outcome**: 11/12 done by end of day. 1 blocked on external vendor.

## Day 2 — Wave 2 + Wave 3 (18 sessions)

Now confident, launched Wave 2 (8 sessions, DevTools/observability work) and Wave 3 (10 sessions, mixed).

**New finding**: a session reported its plan was **already done by past commits**. Status changed to "implicit done" without code change. ~30 minutes spent verifying instead of 4 hours implementing.

**Pattern emerged**: many ~3-month-old plans were already done. Audit sessions became a recognized type.

**Outcome**: 18/18 done or cancelled.

## Day 3 — Wave 4 (10 sessions) — turning point

By Wave 4, methodology was solidifying. But a new problem surfaced:

- Sessions in Wave 4 hit test failures that had been **fixed in Wave 3** but never merged to `main`
- Worktrees still based on `origin/main` couldn't see fixes

The orchestrator's response: a **batch session** that explicitly pulled in fixes from prior Waves. We called it the "999b" recovery session. It produced a branch with all tests passing — useful integration point for later main merges.

**Pattern emerged**: integration branches as main-merge prep tool.

**Outcome**: Wave 4 — 10/10 done. Plus 999b which made the next several Waves safer.

## Days 4-5 — Waves 5-11

Pace accelerated. Waves 5-10 each landed 9-10 done with high quality. The methodology was now mature:

- Mixed compositions (audit + impl + INDEX in each Wave)
- PR/push policy formalized at Wave 9 (we should have done this Day 1)
- Batch sessions used aggressively for "trivially similar plans"
- INDEX consolidation done in batches once children settled

Notable session results:

| Wave | Highlight |
|---|---|
| 5 | Email DOM analysis chain (3 sessions): unlocked weeks of blocked work |
| 6 | "v2 architecture" batch judged 11 plans in one session — 2 done, 9 cancelled |
| 7 | Recovery batch (999b) integrated multiple branches, 366/366 tests passing |
| 8 | INDEX done pattern crystallized — 7 closed in a row using the same template |
| 9 | Security work (anonymous-fallback removal): the user-facing security debt that had bothered the user for months, closed |
| 10 | "Browser tool actions" batch session: 9 plans judged "implicit done" in one session |
| 11 | Meta-Wave: closing audit, main-merge planning, comprehensive test plan, deep tech debt revisit |

## Day 5 — Wave 11 (5 sessions, meta-work)

By Wave 11, all that remained were meta-operations:

1. **Closing audit** — verified all plans accounted for, no straggler
2. **Main merge plan** — written, not executed (planned for the user to drive)
3. **Comprehensive testing plan** — written, with policy for using browser-automation testing as a way to also test the browser-automation tool
4. **Long-standing technical debt** (a transfer-loop bug that had been "minor priority" for months) — reopened, new diagnostics added, new hypothesis isolated to a different repo

All 5 done. Method fully proven.

## Final stats

| Metric | Value |
|---|---|
| Duration | 5 days |
| Waves launched | 11 |
| Sessions launched (cumulative) | ~110 |
| Plans moved to done | ~122 |
| Plans moved to cancelled | 5 |
| Plans blocked (external) | 1 |
| Net backlog reduction | ~127 / 140 = ~91% |
| PRs created (selectively, for security/feature work) | 14 |
| Branches created | ~92 |
| Branches merged to main | 0 (deferred to post-operation phase) |

## What worked

1. **Parallelism actually scaled** — 10x speedup vs. sequential single-session
2. **Sessions talked to user directly** — orchestrator wasn't a bottleneck
3. **Batch sessions** efficient for low-stakes judgments
4. **Implicit-done detection** saved weeks of unnecessary work
5. **`_progress.md` as single source of truth** kept everyone aligned (eventually)
6. **INDEX done pattern** turned hierarchies into closeable structures

## What didn't work and we fixed

1. **`origin/main` staleness** — partially worked around with integration branches (999b pattern). Better fix would be merge between Waves.
2. **`_progress.md` in branches** — declared operational state, kept out of merges going forward.
3. **PR/push policy inconsistency** — fixed at Wave 9. Should have been Day 1.

## What didn't work and we didn't fix

1. **No live session monitoring** — relied on user pasting summaries. Worked at this scale but won't scale further.
2. **Branches never merged to main during the operation** — deferred to post-op merge phase. Risk: deployment lag.
3. **Comprehensive testing always deferred** — by operation end, large test debt. Test phase planned but not executed.

## What we'd do differently

1. Set up integration-branch discipline on Day 1 — merge to main (or a known-good branch) between Waves
2. Put `_progress.md` outside the repo from the start
3. Establish PR/push policy in the kickoff conversation
4. Run a "comprehensive test" Wave every 3 Waves, not "after everything"
5. Track session token costs to optimize batch usage

## Generalization

This method works for any project where:

- Plans are file-based (or can be made so)
- Work is reasonably parallelizable (no single critical path)
- One human can dedicate orchestration time
- AI agent quality is adequate (Claude Code worked; YMMV with other agents)

It doesn't work well for:

- 1-person hobby projects (overhead exceeds benefit)
- Teams of 5+ humans (coordination becomes the bottleneck)
- Projects where every plan is high-risk security-critical
- Codebases with very tightly-coupled modules (worktree independence breaks)

The method is captured in this repo for reuse. The biggest risk in adoption is treating it as a recipe — it's a pattern that needs adaptation. Read [METHODOLOGY.md](../METHODOLOGY.md) and [ANTI-PATTERNS.md](../ANTI-PATTERNS.md) carefully before starting your own engagement.
