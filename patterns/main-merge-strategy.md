# Pattern: Main merge strategy

After Waves, you have **dozens of orphan `plan/<id>` branches** (local — sessions commit but do not push) that need to land on `main`. Naive merging causes conflicts and chaos. This pattern offers a structured approach. Throughout, remember that **sessions only commit**: pushing, opening PRs, and merging to `main` are all user decisions, so this whole phase is human-driven.

It covers two integrations: the **lightweight between-Wave integration** that runs *during* the operation (next section), and the **heavy main-merge** that runs *after* it (the rest of this doc).

## Between-Wave integration (during the operation)

Letting `plan/<id>` branches pile up unmerged is the **#1 anti-pattern**: each new Wave bases its worktrees off a `origin/main` that froze on Day 0, so sessions re-discover already-fixed bugs ([ANTI-PATTERNS #1](../ANTI-PATTERNS.md#1-worktrees-were-created-from-stale-originmain)).

After each Wave:

1. Merge the Wave's `done` branches into a single `integration/latest-known-good` branch
2. Run the suite there — this is where Waves combine, and the natural home for [test Waves](test-waves.md)
3. Base the next Wave's worktrees on it: `git worktree add .worktrees/<id> -b plan/<id> integration/latest-known-good`

Resolve the small conflicts now (~10 branches) rather than deferring them to the ~90-branch main-merge below. This integration branch *is* the "`meta-002`" we built reactively in the original engagement — just kept green from Day 1.

## The problem

In our engagement:
- 11 Waves × ~10 sessions each = ~110 branches potentially created
- After cancellations and consolidations: **~90 actually-want-to-merge branches**
- `_progress.md` touched by 81 of those (operational state in all branches — anti-pattern, see ANTI-PATTERNS.md)
- `main.py`, `setup.html`, `browser_tool_spec.md` each touched by 11+ branches

If you `git merge plan/X1 plan/X2 ... plan/X90` naively, you'll spend days on conflicts.

## The "integration branch" pattern

**Don't merge all 90 branches independently. Find or create a single integration branch that already harmonizes the conflicts.**

### Step 0: Identify the integration branch

In our case, **`plan/meta-002`** emerged as the integration branch. It was the result of a batch session ([batch sessions](batch-sessions.md)) that:

- Cherry-picked from `plan/api-003`, `plan/api-003a`, `plan/ui-004`, `plan/ui-005` (test-recovery work)
- Resolved cross-cutting conflicts
- Ended with **366/366 tests passing**

Once `plan/meta-002` existed, the strategy became: **base everything on `plan/meta-002`**.

### Step 1: Categorize remaining branches by risk/priority

```
Priority A — Security: auth-002a, auth-009, etc. (must merge first, high stakes)
Priority B — Feature group 1: api-018..api-023 (project Write)
Priority C — Feature group 2: corp-* series
Priority D — Feature group 3: intake-* / devtools-* series
Priority E — Docs/chore/INDEX
```

This grouping is project-specific. The point: **don't merge all-at-once or merge-in-arrival-order**. Group, then merge groups in dependency order.

### Step 2: Merge each priority group

For each group:

1. `git checkout plan/meta-002` (or whichever integration branch)
2. Cherry-pick or merge the branches in that group
3. Resolve conflicts (most should be minor if categorized well)
4. Run full test suite
5. Push to a `release/groupN` branch
6. Open one PR for the entire group

(Steps 5-6 are where the user takes over: sessions never pushed or opened PRs, so this phase is the first time these branches leave the local machine.)

This produces **~5 PRs** (one per priority) instead of 90 PRs. Reviewable.

### Step 3: Deploy strategically

For our project (multi-tenant SaaS with one paying tenant):

- After Priority B merges: deploy to staging
- After Priority C merges: deploy to staging again
- After Priority D merges: deploy to production
- After Priority E: documentation update PR, no deploy

Three deployment events instead of one big one. Each catches issues from a smaller surface.

## Identifying "hot files"

Before starting the merge, scan all branches for hot files (touched by many branches):

```bash
# Local branches, since sessions commit without pushing. Swap to
# 'origin/plan/*' only if you've already pushed them for review.
for branch in $(git branch --list 'plan/*' | sed 's/^[* ]*//'); do
  git diff --name-only main..$branch
done | sort | uniq -c | sort -rn | head -20
```

In our engagement, hot files were:

| File | Branches touched |
|---|---|
| `_progress.md` | 81 ⚠️ |
| `main.py` | 11 |
| `setup.html` | 11 |
| `browser_tool_spec.md` | 11 |
| `manifest.json` (chrome ext) | several (version conflicts!) |

The `_progress.md` and `manifest.json` cases are special:

- `_progress.md` — operational state, should not be merged from any branch. See [anti-patterns](../ANTI-PATTERNS.md#2-_progressmd-merge-conflicts-everywhere).
- `manifest.json` — version field needs explicit reconciliation. Pick the highest version + integrate features.

Plan for hot files **before** starting merges. For each:

- Decide who "owns" the merged version
- Document the merge strategy in the integration branch

## Identifying local-only branches and uncommitted work

In v2, **local branches are the normal state** — sessions commit but never push, so every `plan/<id>` branch lives only on your machine until the user decides to merge or push it. The risk is not "unpushed" (that's expected) but **losing a branch's commits when its worktree is removed**, or leaving uncommitted changes behind. Check before deleting any worktree:

```bash
# All local plan branches and their last commit
git for-each-ref --format='%(refname:short) %(committerdate:relative)' refs/heads/plan/

# Any worktree with uncommitted changes? (these would vanish on worktree removal)
for wt in .worktrees/*/; do
  echo "== $wt =="; git -C "$wt" status --short
done

# Optional, only if you have already pushed some for review:
# branches that exist locally but not on origin
comm -23  <(git branch --list 'plan/*' | sed 's/^[* ]*//' | sort) \
          <(git branch -r --list 'origin/plan/*' | sed 's|origin/||' | sort)
```

Confirm every worktree is clean (all work committed to its `plan/<id>` branch) before you delete it. We almost lost work this way (`plan/auth-026` and `plan/api-026` had uncommitted changes in their worktrees at one point).

## When conflicts can't be auto-resolved

Some files will conflict because the work was genuinely conflicting. Strategies:

- **Refactor in the integration branch**: take both changes, refactor to coexist
- **Choose latest**: if both edits are stale, take the latest plan's version
- **Ask the affected session's author**: a session may have to be re-opened to re-resolve

We had ~3-4 substantive conflicts that required real thought. Most were trivial line-additions in different functions.

## Deployment timing recommendations

For a project with paying customers:

```
Pre-merge phase                            : Establish "test before merge" CI guard
Priority A (security)                      : Merge, deploy to staging, smoke test
Priority B (high-impact features)          : Merge, deploy to staging, customer-relevant smoke test
Priority C (medium features)               : Merge, batch in staging
Priority D (lower-impact)                  : Merge
Priority E (docs/chore)                    : Merge, no deploy needed
Production deployment                      : After each completed priority group, on a planned window
```

For a personal project:

```
Just merge in priority order. Deploy at the end.
```

## Real example: our merge plan

The `main-merge` session in Wave 11 produced `docs/main_merge_plan.md` (10 chapters), which described:

- 92 branches to merge
- 5 priority groups
- 4 hot files with named owners for the merge
- 3 deployment events (after groups B, C, D)
- 2-3 expected substantive conflicts

This plan was **for the user to execute later** — the session didn't run the merges. This is by design: large merges to `main` should be human-driven.

## Anti-patterns

- ❌ "Just merge them all" — guaranteed multi-day conflict resolution session
- ❌ Random merge order — increases conflict resolution
- ❌ Skipping the hot-file analysis — surprised by `manifest.json` version war
- ❌ Letting `_progress.md` (or other operational state) into any merge — see anti-patterns
- ❌ All-at-once deployment — too much risk surface

## Tool support

These are useful during the merge phase:

```bash
# Show branches and their last activity (use refs/heads/plan/ for the
# local-only branches sessions produce; refs/remotes/origin/plan/ if pushed)
git for-each-ref --format='%(refname:short) %(committerdate:relative) %(authoremail)' refs/heads/plan/

# Find branches with no recent activity (might be safely closed)
git for-each-ref --format='%(refname:short) %(committerdate:short)' refs/heads/plan/ | sort -k2

# Conflict prediction
git merge-tree $(git merge-base main plan/X) main plan/X | grep '<<<<<<' | wc -l
```

## TL;DR

1. Don't merge all-at-once
2. Find/create one good integration branch
3. Categorize remaining branches by priority/risk
4. Merge in priority order
5. Plan hot-file resolution upfront
6. Deploy in stages
