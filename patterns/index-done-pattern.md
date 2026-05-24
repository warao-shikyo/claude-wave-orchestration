# Pattern: INDEX done

An INDEX plan summarizes and tracks child plans. When all children are settled, the INDEX session **closes the parent** with a summary table — no new code needed.

## When to use

Your project organizes work as hierarchies:

```
INDEX plan (e.g. "Feature group X")
├── Child plan A
├── Child plan B
├── Child plan C
└── Child plan D
```

When children are all `done`, `cancelled`, or `blocked` (with clear external dependency), the INDEX should close too.

## When NOT to use

- Children are still in progress
- INDEX itself describes work beyond just "collect children"
- INDEX has its own implementation criteria

## Workflow

A Wave includes the INDEX as a session target. That session:

1. Reads each child plan MD
2. Confirms each child's final status (`done` / `cancelled` / `blocked`)
3. Writes a **completion summary table** in the INDEX MD
4. Writes a **residual issues list** (anything not done at the INDEX level, often deployment / E2E testing)
5. Closes the INDEX MD as `done`
6. Updates `_progress.md`

**No new code.** The session reads, summarizes, closes. ~30 min of work.

## The summary table format

In the INDEX MD, add a section like:

```markdown
## Child plan completion summary

| Child ID | Title | Status | Commit | Branch | Notes |
|---|---|---|---|---|---|
| X1 | ... | done | abc1234 | plan/X1 | ... |
| X2 | ... | done | def5678 | plan/X2 | ... |
| X3 | ... | cancelled | — | — | obsoleted by Y |
| X4 | ... | blocked | hij9012 | plan/X4 | external dep on Z |
```

The table is the **audit trail** for the INDEX's closure.

## The residual issues list

Things the INDEX should record as "still pending after closure":

```markdown
## Residual issues (post-INDEX closure)

These items are not in scope for this INDEX but flagged for follow-up:

- E2E testing for all children (deferred to test phase)
- Cloud Run deployment of children's branches
- Performance monitoring once deployed
- (etc.)
```

This is **not** new work — it's documenting known gaps so future readers don't think the work is more complete than it is.

## Closing condition variations

| Variant | When | Note |
|---|---|---|
| **Strict done** | All children `done` | Pure case |
| **Done with cancels** | All children `done`/`cancelled`, none blocked | Common — explain cancels |
| **Done with externals** | Some children `blocked` on external dependencies | INDEX still closes — record what's external |
| **Partial close (ready)** | Most children done, one or two still in progress | INDEX stays `ready`, closes later |

The "Done with externals" case is important: don't keep an INDEX open forever waiting for an external dependency. Close it with the dependency noted, and the dependency becomes a separately-tracked item.

## Real example

Our engagement closed 7 INDEX plans this way in rapid sequence:

```
INDEX 750 (corp_org AI integration)         — closed first, set the template
INDEX 800 (devtools observability)
INDEX 810 (HTTP replay)
INDEX 830 (project Write completion)
INDEX 820 (documentation)
INDEX 500 (universal reception service)
INDEX 600 (service completion)
```

Each followed the same pattern: read children, write summary table, write residual issues, close. The first one took ~45 minutes; later ones were faster because the format was established.

The session for INDEX 600 introduced a useful variant: **child plan 603 was blocked** on an external dependency (waiting for a vendor to approve regulatory paperwork). Rather than keep INDEX 600 open indefinitely, the session closed it with "completion criteria met for design/implementation; external dependency tracked separately."

## Why this is a "pattern" not just "common sense"

Because the temptation is to keep INDEXes open "until everything is really done." That makes them sticky, accumulate baggage, and lose their summary value.

The pattern says: **close the INDEX once the work it represents is done at the work level**. Deployment, testing, monitoring — those are separate concerns.

## Anti-patterns

- ❌ Keeping INDEX open until production deployment (too sticky)
- ❌ Closing INDEX without a summary table (loses audit value)
- ❌ Closing INDEX without listing residual issues (false confidence)
- ❌ Implementing the INDEX session as a "verify and possibly fix children" session — it's a summary session, no fixing

## Tip: Reusable summary table generator

If you have many INDEXes to close, automate the summary table generation:

```python
# Pseudo-code — adapt to your plan MD format
def summarize_children(parent_id):
    children = find_child_plans(parent_id)
    rows = []
    for child in children:
        rows.append({
            "id": child.id,
            "title": child.title,
            "status": child.status,
            "commit": find_commit(f"plan/{child.id}"),
            "branch": f"plan/{child.id}",
            "notes": child.summary,
        })
    return rows
```

We didn't automate this in our engagement — each INDEX session did it manually — but the work is repetitive enough to be worth scripting if you have 7+ to do.
