# {AREA}-{NNN}-{slug} — {Title}

<!--
Filename: <area>-<NNN>-<slug>.md  (e.g. auth-001-oauth-login.md)
When done, rename to <area>-<NNN>-<slug>_done.md — completion is a file rename,
not a Status edit. See INSTRUCTIONS.md.
-->

## Status
draft

<!--
Lifecycle: draft → ready → in_progress → done | cancelled | blocked

Status transitions:
- draft → ready    : This plan is fleshed out enough to launch a session
- ready → in_progress : Session has been launched
- in_progress → done : Plan is complete — rename file to ..._done.md (don't edit this field to "done")
- in_progress → cancelled : Plan no longer relevant (set this field to "cancelled" + reason in execution log)
- in_progress → blocked : External dependency stops progress (set this field to "blocked" + reason in execution log)
-->

## Purpose

<!-- Why this plan exists. 1-2 paragraphs, plain prose. -->

## Background

<!--
Context. What's the situation that requires this work.
- What problem are we solving?
- What's the current state?
- Why now?
-->

## Scope

<!-- What's in scope. List specific things this plan covers. -->

- ...

## Out of scope

<!--
What's NOT in scope. Important — sets boundaries.
Things that might seem related but aren't this plan's job.
-->

- ...

## Completion criteria

<!--
Objective, testable conditions that say "this plan is done."
Use checkboxes. The session must verify each one before declaring done.
-->

- [ ] ...
- [ ] ...
- [ ] existing test suite still green (no regression)
- [ ] verified manner: <unit | integration | manual | NOT VERIFIED — deferred to test Wave>

## Notes / risks / open questions

<!-- Anything the session should know upfront. -->

## Related

<!--
Links to:
- Other plan IDs (<area>-<NNN>)
- Memory entries
- Docs
- External references
-->

- ...

<!--
Push / PR / merge policy: there is no per-plan override. The session master's
responsibility ends at commit. Push, PR, and merge to main are always the user's
decision. Deploy from the worktree for verification only is allowed. See INSTRUCTIONS.md.
-->

## Execution log

<!--
Append-only. Each entry: ISO date + what happened. Log progress line-by-line.
Examples:

2026-MM-DD started by session plan-auth-001
- discovered X, decided Y
- committed abc1234 (feat(plan-auth-001): ...) — local branch only, not pushed

2026-MM-DD completed
- verdict: done (all 3 criteria met, evidence: commits abc1234, def5678)
- renamed to auth-001-<slug>_done.md, committed chore(plan-auth-001): mark done
-->

- YYYY-MM-DD created
