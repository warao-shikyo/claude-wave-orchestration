# Pattern: Test Waves

In the original engagement, almost every session ended with *"real E2E testing is out of scope; that's for a separate test phase."* After 122 plans we had a massive, unscheduled testing backlog (see [ANTI-PATTERNS.md #10](../ANTI-PATTERNS.md#10-comprehensive-testing-was-deferred-without-a-date)). Velocity was real, but the test debt came due all at once at the worst time — right before deployment.

This pattern keeps test debt bounded by **interleaving dedicated test Waves into the operation** instead of deferring all testing to "after."

## The principle

> Every ~3 build Waves, run 1 test Wave. Never let more than ~3 Waves' worth of unverified work accumulate.

A **build Wave** ships features/fixes (the normal Wave). A **test Wave** ships nothing new — its sessions verify that the previous build Waves' work actually holds together.

## Why interleave instead of defer

| Deferred testing (what we did) | Interleaved test Waves |
|---|---|
| Test debt grows unbounded | Bounded to ~3 Waves of work |
| Failures surface at deploy time | Failures surface within ~3 Waves of being introduced |
| Hard to attribute a failure to a plan | Recent, small surface — easy attribution |
| One terrifying QA phase | Several small, routine verification passes |

The cost is real: test Waves don't reduce the backlog count, so they *feel* slow. Budget for them anyway — the alternative is the deploy-time pileup.

## Two layers of "testing"

### Layer 1 — Definition-of-Done per plan (every build Wave)

Each plan's **completion criteria** must include at least a minimal verification, not just "code written." See [templates/INSTRUCTIONS.md](../templates/INSTRUCTIONS.md) — the plan MD's `Completion criteria` should distinguish:

```markdown
## Completion criteria
- [ ] code implements X
- [ ] unit tests for X pass (N/N)
- [ ] existing suite still green (no regression)
- [ ] verified manner: <unit | integration | manual | NOT VERIFIED — deferred to test Wave>
```

That last line is the honest one. A session is allowed to ship `NOT VERIFIED — deferred to test Wave`, but it must **say so** — that's what a later test Wave picks up. Silent "looks done" is the failure mode (see also [ANTI-PATTERNS.md #11](../ANTI-PATTERNS.md#11-we-didnt-establish-whats-the-production-reality-baseline)).

### Layer 2 — Test Wave (every ~3 Waves)

A test Wave is composed of sessions whose only job is verification of recently-shipped work. Compose it from:

- Plans whose summary said `NOT VERIFIED — deferred`
- Plans that touched **hot files** (see [main-merge-strategy.md](main-merge-strategy.md)) — high blast radius
- Cross-cutting findings logged in `_progress.md` that smell like regressions
- The integration branch (see [between-Wave integration](main-merge-strategy.md#between-wave-integration-during-the-operation)) — run the **full** suite there, since that's where Waves combine

A test-Wave session does **not** implement features. If it finds a bug, it logs it as a new plan for a future build Wave (or fixes it only if trivial and in-scope), exactly like any audit session.

## Sequencing example

```
Wave 1   build
Wave 2   build
Wave 3   build
Wave 4   TEST   ← verify Waves 1-3 on the integration branch; file regressions as new plans
Wave 5   build  (includes regressions found in Wave 4)
Wave 6   build
Wave 7   build
Wave 8   TEST   ← verify Waves 5-7
...
Wave N   TEST   ← final comprehensive pass before main-merge / deploy
```

The final Wave is still a comprehensive test pass — but it's now *confirmation*, not *discovery*, because the interim test Waves already caught most regressions.

## Starter prompt variant

See [templates/starter-prompt-template.md](../templates/starter-prompt-template.md) "Variant for test-Wave sessions". Sketch:

```
あなたは plan {PLAN_ID} ({area}-{NNN}) の検証セッションです。新規実装はしません。
対象: {TARGET_PLANS} で出荷されたコードが実際に動くかを検証。
手順: 統合ブランチ上で対象のテストを実行し、回帰を探す。
発見したバグは新規 plan として提案（軽微かつ範囲内なら修正可）。
判定: verified / regressions-found(リスト) / cannot-verify(理由)。
成果は commit のみ（push / PR / merge はユーザー判断）。検証完了なら plan を `<id>-<slug>_done.md` にリネーム。
```

## Relationship to deployment baseline

A test Wave verifies "code present in the branch works." It does **not** verify "running in production" — that's the deployment-baseline concern (see [METHODOLOGY.md §0](../METHODOLOGY.md#0-kickoff-capture-the-baseline)). Keep the two distinct: a test Wave can pass while production is still running last month's code.

## TL;DR

1. Every plan's DoD states how it was verified — `NOT VERIFIED — deferred` is allowed but must be explicit.
2. Run a test Wave every ~3 build Waves; never accumulate more than ~3 Waves of unverified work.
3. Test Waves ship no features; they verify, and file regressions as new plans.
4. Run the full suite on the integration branch, where Waves combine.
5. The final comprehensive pass becomes confirmation, not discovery.
