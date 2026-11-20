# {AREA}-{NNN}-{slug} — {Title}

<!--
Filename: <area>-<NNN>-<slug>.md  (e.g. auth-001-oauth-login.md)
When done, rename to <area>-<NNN>-<slug>_done.md — completion is a file rename,
not a Status edit. See INSTRUCTIONS.md.
-->

## Status
draft

<!--
Values: draft | ready | cancelled | blocked   (done is a file rename, not a value here)

- draft  : not settled yet — the orchestrator won't launch it
- ready  : "OK to launch" — only set this when it really is
- done   : the master renames the file to ..._done.md and commits `chore(plan-<id>): mark done` (terminal)
- cancelled : no longer relevant (set this field + reason in execution log; no rename)
- blocked   : external dependency stops progress (set this field + reason; no rename).
              Waiting for a deploy is NOT blocked — post-deploy checks go to the inbox `verify:` line.

After done the orchestrator tracks merged → deployed → verified in _progress.md (see INSTRUCTIONS.md).
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
Checks that need a deploy are not done-conditions for the master: mark them
"→ verify (checked by the orchestrator after deploy)" and put them in the inbox `verify:` line.
-->

- [ ] ...
- [ ] ...
- [ ] existing test suite still green (no regression)
- [ ] verified manner: <unit | integration | manual | NOT VERIFIED — deferred>

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
Landing policy: there is no per-plan override. The session master's responsibility
ends at commit (and mark done). Push / PR are the user's call; merge to main and deploy
are the orchestrator's steps, each with user approval. A master never deploys from its
worktree. If the order of rollout matters (e.g. code first, config second), say so in Notes.
-->

## Execution log

<!--
Append-only. One line per checkpoint (a commit, verifying a criterion, asking the
user, stopping): when / what / which commit. No line-by-line narration.
Examples:

2026-MM-DD started by session plan-auth-001
- discovered X, decided Y
- committed abc1234 (feat(plan-auth-001): ...) — local branch only, not pushed

2026-MM-DD completed
- verdict: done (all 3 criteria met, evidence: commits abc1234, def5678)
- renamed to auth-001-<slug>_done.md, committed chore(plan-auth-001): mark done
-->

- YYYY-MM-DD created
