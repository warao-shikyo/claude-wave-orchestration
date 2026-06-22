# Pattern: Batch sessions

One session that processes **many related plans in a single sitting**, instead of spawning a session per plan.

## When to use

You have multiple plans that:

- Are **similar in shape** (e.g. "is this draft plan still relevant?", "did this implementation actually land?")
- Each requires **minutes** of judgment, not hours of implementation
- Have **low risk of cross-contamination** (one decision doesn't break another)
- Don't need deep per-plan dialogue with the user

Examples we used:

| Batch ID | Scope | Items | Outcome |
|---|---|---|---|
| `meta-001` | v2-era draft plans, are they still relevant? | 11 | 2 done, 9 cancelled |
| `meta-002` | Test failures from past plans not merged | 23 failing tests | All passing on integration branch |
| `meta-003` | v2-era "ready" plans | 3 | 2 done, 1 maintained as ready |
| `meta-004` | Chrome extension actions | 9 | All "implicit done" |
| `meta-005` | Final audit — anything still uncategorized? | All plans | 0 missed |

5 batch sessions retired **~50 items** efficiently.

## When NOT to use

- Plans need **substantial implementation** (≥ 1 hour each)
- Plans are **independent in non-obvious ways** (one might block another)
- User wants **per-plan visibility** (e.g. for stakeholder reporting)
- Plans are **high-risk** (e.g. security-sensitive cancellation reasoning)

## Structure of a batch session

The session's plan MD says: "Here are 11 plans. Judge each one. For each, write the reasoning. Update `_progress.md` for each."

### Inputs the session needs
- All N plan MDs in the worktree (copy them at seed time)
- Current `_progress.md`
- Project context for inferring "implicit done" status
- Optional: prior batch sessions' verdicts as reference

### Outputs the session produces
- Each plan MD updated with status + reasoning
- `_progress.md` rows updated
- A summary table (status × count) to report to orchestrator

### Decision framework for the batch session

For each plan, decide one of:

| Verdict | When |
|---|---|
| **done (implicit)** | The plan's goal is already achieved in current code |
| **cancelled** | The plan is no longer relevant (architecture shift, requirement change, etc.) — record *why* |
| **ready (maintain)** | Still relevant, but actual implementation is for a future Wave |
| **blocked** | External dependency prevents progress — record what's blocking |

The reasoning is **mandatory**. A future reader (or auditor) must be able to understand why each verdict was given.

## Starter prompt for a batch session

Keep it short. Reference the plan MD, which has the details.

```
あなたは plan {BATCH_ID} ({BATCH_FILENAME}) を done まで持っていく一括精査セッションです。

タスク: {DOMAIN} 系の {N} 件のプランを順次精査し、cancelled / done / ready のいずれかに判定。

先例: {PRIOR_BATCH_ID} ({PRIOR_BATCH_COMMIT}) と同型パターン。

worktree 内に {N} 件の plan MD がコピー済。

判定根拠を必ず各 plan MD の実行ログに残す。終了時に _progress.md の該当行を更新。

成果は commit のみ（push / PR / merge はユーザー判断）。done にした plan は `<id>-<slug>_done.md` にリネーム。
```

## Risk: batch sessions can produce shallow verdicts

A session that has to make 11 decisions in 90 minutes can rush. Mitigations:

- Set a minimum quality bar: every "cancelled" needs ≥ 2 sentences of reasoning, every "implicit done" needs a commit hash or file pointer as evidence
- Have the user spot-check a sample of the verdicts
- For high-stakes domains (security, financial), avoid batches — give each plan its own session

## Cost vs sequential

In our case:

| Approach | Time | Sessions |
|---|---|---|
| One session per plan, 11 plans | ~22 hours of total session time | 11 |
| Batch session for 11 plans | ~2 hours of session time | 1 |

~10x speedup for low-complexity decisions. The right tool for "yes/no/why" judgments.

## Real example: the `meta-` family

We named the batch sessions `meta-001` through `meta-005` to mark them as orchestration-meta, not project work.

```
plan meta-001 — v2 draft plans batch        (Wave 6)
plan meta-002 — test failure recovery batch (Wave 7) — integrated multiple fix branches
plan meta-003 — v2 ready plans batch        (Wave 9)
plan meta-004 — Chrome extension actions    (Wave 10)
plan meta-005 — final audit                 (Wave 11)
```

Convention: orchestration-meta plans use the `meta-` area prefix; project plans use domain areas like `auth` / `billing` / `ui`. Systems are never distinguished by number band — the area prefix carries that meaning, which keeps project plan IDs self-describing.

## Variants

### "Audit" batch
Read-only verdicts (no code change). Useful for "what's actually done?" at any point in the operation.

### "Recovery" batch (like `meta-002`)
Pull in commits/fixes from multiple non-merged branches, resolve conflicts, produce one ready-to-merge branch.

### "Sweep" batch
End-of-operation cleanup — every remaining plan gets a final status.

## Anti-patterns

- ❌ Batch sessions for high-stakes implementation work — too rushed
- ❌ Batch sessions across very different domains — judgment quality drops
- ❌ Batch sessions without per-item reasoning — useless audit trail
- ❌ Treating "batch" as a synonym for "fast" — quality matters more
