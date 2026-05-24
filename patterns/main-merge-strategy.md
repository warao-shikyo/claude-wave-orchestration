# Pattern: Main merge strategy

After Waves, you have **dozens of orphan `plan/<id>` branches** that need to land on `main`. Naive merging causes conflicts and chaos. This pattern offers a structured approach.

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

In our case, **`plan/999b`** emerged as the integration branch. It was the result of a batch session ([batch sessions](batch-sessions.md)) that:

- Cherry-picked from `plan/415`, `plan/415a`, `plan/422`, `plan/423` (test-recovery work)
- Resolved cross-cutting conflicts
- Ended with **366/366 tests passing**

Once `plan/999b` existed, the strategy became: **base everything on `plan/999b`**.

### Step 1: Categorize remaining branches by risk/priority

```
Priority A — Security: 402a, 759, etc. (must merge first, high stakes)
Priority B — Feature group 1: 418-423 (ielove Write)
Priority C — Feature group 2: corp_org/750 series
Priority D — Feature group 3: 500/600/800 series
Priority E — Docs/chore/INDEX
```

This grouping is project-specific. The point: **don't merge all-at-once or merge-in-arrival-order**. Group, then merge groups in dependency order.

### Step 2: Merge each priority group

For each group:

1. `git checkout plan/999b` (or whichever integration branch)
2. Cherry-pick or merge the branches in that group
3. Resolve conflicts (most should be minor if categorized well)
4. Run full test suite
5. Push to a `release/groupN` branch
6. Open one PR for the entire group

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
for branch in $(git branch -r --list 'origin/plan/*'); do
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

## Identifying unpushed branches

Some sessions commit locally but don't push. Catch them before they're lost:

```bash
# List remote branches
git branch -r --list 'origin/plan/*'

# List local branches
git branch --list 'plan/*'

# Diff: branches that exist locally but not on origin
comm -23  <(git branch --list 'plan/*' | sed 's/^[* ]*//' | sort) \
          <(git branch -r --list 'origin/plan/*' | sed 's|origin/||' | sort)
```

Push these before you delete worktrees. We almost lost work this way (plan 604 and plan 426 had local-only commits at one point).

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
# Show branches and their unmerged commit count
git for-each-ref --format='%(refname:short) %(committerdate:relative) %(authoremail)' refs/remotes/origin/plan/

# Find branches with no recent activity (might be safely closed)
git for-each-ref --format='%(refname:short) %(committerdate:short)' refs/remotes/origin/plan/ | sort -k2

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
