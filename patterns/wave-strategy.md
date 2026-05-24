# Pattern: Wave strategy

A "Wave" is **one cycle of: plan → launch → execute → summarize → integrate**, with N (typically 10) sessions in flight.

## When to use

You have a backlog of work and want to clear it methodically with **parallel execution** and **periodic synchronization**.

## When NOT to use

- Backlog < 10 items: skip Waves, run single sessions
- Items are tightly coupled: parallelism won't help, do sequentially
- You can't dedicate orchestrator time during Wave execution: this is parallel-but-not-autonomous

## Wave sizing

Pick N (sessions per Wave) by:

| N | When |
|---|---|
| 3-5 | First Wave to validate the method, or when sessions need heavy user interaction |
| **8-12** | **Default sweet spot** |
| 13+ | Only if you've automated parts (e.g. starter prompts, _progress.md updates) and sessions are mostly independent |

Larger Waves stress:
- `~/.claude.json` write contention (file lock during launcher's trust-registration step)
- User cognitive load (each session opens its own conversation)
- Orchestrator's `_progress.md` update tempo

## Composing a Wave

For each Wave, prefer a mix:

```
Wave composition formula:
- 1-2 INDEX/aggregate plans (low complexity, build momentum)
- 2-3 implementation plans (medium complexity, advance the codebase)
- 1-2 batch / audit plans (clean up backlog cheaply)
- 1 high-risk or large-scope plan (the "hero plan" — may carry the wave)
- 2-3 follow-ups from prior Wave findings
```

This is a guide, not a law. The point is to avoid all-the-same-kind Waves that exhaust user patience.

## Sequencing across Waves

Across multiple Waves, the pattern that worked for us:

1. **Wave 1**: Pick visible, mid-difficulty plans. Validate the method, build confidence.
2. **Waves 2-3**: Expand to independent plans across multiple domains.
3. **Waves 4-5**: Now you have data — Wave 1-3 surfaced cross-cutting issues. Address those.
4. **Waves 6-8**: Pick "implicit done" candidates and INDEX consolidations. Cheap wins.
5. **Waves 9-10**: Finishing wave. Pick up the stragglers, force-resolve blocked items where possible.
6. **Wave 11+**: Meta-work (testing plan, merge orchestration, retrospectives).

We did 11 Waves over 5 days for a ~140-item backlog. Your scale will vary.

## Between Waves

After each Wave completes (all rows are `done|cancelled|blocked`):

1. **Update master `_progress.md`** — reflect all outcomes
2. **Note cross-cutting findings** — what did sessions independently discover?
3. **Identify follow-ups** — new plans needed? Add to candidate list.
4. **Decide: merge to main now or defer?** — see [main merge strategy](main-merge-strategy.md)
5. **Pick next Wave's plans** — apply composition formula above

The "between" gap shouldn't be long — momentum matters.

## Pacing within a Wave

Stagger session launches by **5-6 seconds**, not all at once:

- Lets each launcher complete its `.claude.json` registration without contention
- Lets the Claude Code prompt cache populate (5-minute TTL)
- Spreads load on user (the user starts seeing session prompts in sequence, not 10 at once)

```bash
# Pseudo-orchestration
for plan_id in $WAVE; do
  python launch_claude.py .worktrees/$plan_id "<starter prompt>"
  sleep 5
done
```

## Detecting "Wave done"

A Wave is **complete** when `_progress.md` shows all that Wave's rows as `done`, `cancelled`, or `blocked` (with reason).

Common pitfall: sessions sometimes silently close without an explicit "done." Check periodically:

```bash
git log --all --oneline --since='2 hours ago' | grep 'plan-'   # what's actually shipped
ls .worktrees/                                                  # what worktrees exist
```

If a session's worktree exists but has no recent commits, ask the user.

## Wave anti-patterns

- ❌ **Launching all 100 sessions at once** — user can't keep up, `.claude.json` thrashes
- ❌ **Waiting for the perfect plan composition** — pick reasonable mix and go
- ❌ **Re-launching halfway through** — if a Wave is going poorly, complete it then adjust next Wave, don't disrupt mid-flight
- ❌ **Treating Wave size as fixed forever** — adjust based on observed outcomes
- ❌ **Skipping the between-Wave merge** — branches pile up (see [main merge strategy](main-merge-strategy.md))

## Real example

Wave 6 from our engagement (10 sessions, mixed composition):

```
| ID    | Type                   | Outcome                              |
|-------|------------------------|--------------------------------------|
| 420   | Implementation re-run  | done (was blocked on prior wave)     |
| 421   | Implementation re-run  | done                                 |
| 415a  | New plan from finding  | done (test-suite fix)                |
| 999   | Batch (11 items)       | done (2 done, 9 cancelled)           |
| 503   | Implementation         | done                                 |
| 509   | Implementation         | done                                 |
| 510   | Implementation         | done                                 |
| 603   | Implementation         | blocked (external dependency)        |
| 818   | Bug fix                | done                                 |
| 819   | Stability hardening    | done                                 |
```

9 done, 1 blocked (external). Mix of types meant momentum stayed high. The batch session (999) alone retired 11 items.
