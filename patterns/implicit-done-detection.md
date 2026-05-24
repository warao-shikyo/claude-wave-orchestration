# Pattern: Implicit-done detection

A "TODO" plan may actually be **already completed by past commits** — the team forgot to close it. Detecting this is faster than re-implementing.

## When to use

You have plans that have been sitting around for a while, and you suspect some are stale. Specifically:

- Plans in `draft` or `ready` for **weeks**
- Project has had **substantial activity** since the plan was written
- Plan's completion criteria are **objective** (specific files, specific test names, specific endpoints)

## When NOT to use

- Brand new plans (< 1 week old)
- Plans where success is **subjective** (e.g. "improve developer experience")
- High-risk plans where you'd want to re-verify even if "looks done"

## The verdict spectrum

| Verdict | Meaning |
|---|---|
| **implicit done** | Implementation is in code, matching the plan's criteria |
| **side-effect done** (副次達成) | Plan's criteria met via a different feature path than originally planned |
| **partial done** | Some criteria met, some not — record what's left |
| **cancelled (obsoleted)** | Criteria no longer relevant due to architectural shifts |

The first two ("done") are dispositionally similar but the **reasoning trail must distinguish them**, so future auditors understand what happened.

## Detection workflow

The session assigned to a plan:

### 1. Read the plan's completion criteria

What does the plan say "done" means? Look for:
- Specific files to be created/modified
- Specific test names that should pass
- Specific endpoints/routes/commands that should exist
- Specific behavior that should be observable

### 2. Check the current code against each criterion

Use `git log -- <path>`, `grep`, file existence checks, test execution.

### 3. Categorize the match

```
All criteria met by existing code      → implicit done
Criteria met by *equivalent* features  → side-effect done (explain why "equivalent")
Some criteria met                       → partial done (list remaining)
Criteria irrelevant now                 → cancelled (explain why)
```

### 4. Write a reasoning trail

In the plan MD's execution log:
- Date of audit
- What was checked
- Commit hashes / file paths that constitute "evidence"
- The verdict

### 5. Update status

Plan MD: `draft` → `done` (or `cancelled`)
`_progress.md`: status column updated, notes column includes commit hash references

## Why "implicit done" beats "re-implement"

| Metric | Re-implement | Implicit done audit |
|---|---|---|
| Time | 2-8 hours | 20-40 minutes |
| Token cost | High | Low |
| Risk of regression | High (you're changing code) | Zero (no code change) |
| Project clarity | Confused (two impls?) | Clean (audit trail) |

In our engagement, **dozens of plans** were closed via this pattern. Estimated savings: weeks of unnecessary work.

## Patterns within the pattern

### "Already in main, branch is stale"
You check the plan's criteria — they're met. The implementation is already on `main`. The plan was created before someone shipped the work and nobody closed the plan.

Verdict: `implicit done`, evidence: `git log -- <file>` shows commit dated before plan creation.

### "Done in a different way" (side-effect done)
The plan said "add feature X via API endpoint Y." But the codebase implemented feature X via WebSocket bridge Z. The user-visible behavior is identical.

Verdict: `side-effect done`. The reasoning explicitly says "criteria met via different mechanism — original spec's API endpoint was not added, but feature works."

This matters because if you didn't note "side-effect done," a future reader might think the API endpoint exists when it doesn't.

### "Plan was wrong" (cancelled)
The plan said "implement X using library Y." But Y has been removed from the codebase, replaced with Z. Implementing X with Y is no longer possible or desirable.

Verdict: `cancelled`. Reasoning: "Library Y replaced by Z in commit abc123. Plan's premise is invalid."

### "Tests exist but feature doesn't run"
The plan says "implement feature X." Tests for X exist (and pass). The feature code is present. But nobody verified it's deployed and running in production.

Verdict: ambiguous. Either:
- `implicit done` with note "deployed status unverified, needs production check"
- `partial done` with the deployment check as the remaining work

We chose the partial path; pick whichever your project's culture prefers.

## Risks

### Audit theater
A session that just says "looks done" without evidence is worse than useless — it creates false confidence.

Mitigation: **require evidence**. Commit hashes, file paths, test names. No bare assertions.

### Missing the "almost done"
Easy to miss: the plan is 90% done but missing one critical piece. Audit declares "done" overconfidently.

Mitigation: read **every criterion**. If unsure, say `partial done` and list the gap.

### Drift
Audit verdict made today may be wrong tomorrow if the code changes. Audit results are point-in-time.

Mitigation: include the date and the audited commit hash in the verdict.

## Reasoning format

In the plan MD, append something like:

```markdown
## Execution log

2026-XX-XX — Implicit done audit by session plan-NNN
- Criterion 1 (X file exists): ✓ — present at `path/to/X.py`, last modified `abc1234` (2026-YY-ZZ)
- Criterion 2 (test passes): ✓ — `pytest tests/test_X.py` 12/12 PASS
- Criterion 3 (API endpoint registered): ✓ — `main.py:42` registers `bp_X`
- Verdict: **done (implicit)**. Plan implementation was completed by commit abc1234 (2026-YY-ZZ) and shipped to production at deploy 5678. Plan was never closed administratively.
```

This is auditable. A future reader can verify each line.

## Real example

In our engagement, plan 432 ("customer history by phone benchmark") was sitting in `draft`. The Wave 8 session that picked it up found:

- Tool `customer_history_by_phone_tool` already existed in `main` (commit `8de44f2`, 2026-05-04)
- Tool already deployed (Cloud Build `031604dc`)
- Tool already registered in MCP
- Tool already used by benchmark plan 433

Total session time: about 30 minutes for the audit. Outcome: `done (implicit)`. Saved: weeks of "let me reimplement this..."

This pattern came up so many times that we built a starter-prompt variant specifically for "audit-first" sessions:

```
"Plan {ID} has been in {STATUS} for a while. Before implementing anything,
audit whether the plan is already done. Look for: {criteria}. If done,
update plan MD with evidence and verdict. If not done, then implement.
Either way, finish with a clear status."
```

## Anti-patterns

- ❌ Verdict without evidence (audit theater)
- ❌ Auto-marking everything as "implicit done" without reading criteria
- ❌ Cancelling plans because they're old (without checking if criteria are still relevant)
- ❌ Re-implementing without auditing first (wasted work)
