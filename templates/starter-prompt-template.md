# Session starter prompt template

This is what the orchestrator passes to `launch_claude.py` to launch a main session for one plan.

## Variables to substitute

- `{PLAN_ID}` — e.g. `101`
- `{PLAN_FILENAME}` — e.g. `101_add_user_search.md`
- `{PLAN_TITLE_SHORT}` — e.g. `User search`
- `{KEY_CONTEXT}` — 1-2 sentences specific to this plan (recent activity, dependencies, etc.)
- `{PR_POLICY}` — `PR required` / `PR recommended` / `no PR needed`

## Minimal version (≤200 chars equivalent)

```
あなたは plan {PLAN_ID} ({PLAN_FILENAME}) を done または cancelled まで持っていく独立担当セッションです。

worktree: .worktrees/{PLAN_ID}/、branch: plan/{PLAN_ID}、base: origin/main。

最初に .claude/plans/INSTRUCTIONS.md と .claude/plans/{PLAN_FILENAME} と .claude/plans/_progress.md を読んで開始してください。

権限: ユーザーに直接質問可・commit・push・PR 作成・cancelled 判断すべて自由。
責務: plan MD のステータス・実行ログ更新、_progress.md 自分の行更新、commit メッセージに plan-{PLAN_ID} を含める。
禁止: 他 worktree 直接編集、main 直接 push、.gitignore の .worktrees/ 削除。

開始してください。
```

## With context (recommended)

```
あなたは plan {PLAN_ID} ({PLAN_FILENAME}) を done/cancelled まで持っていく独立担当セッションです。

worktree: .worktrees/{PLAN_ID}/、branch: plan/{PLAN_ID}、base: origin/main。

最初に読むもの:
1. .claude/plans/INSTRUCTIONS.md (plans 運用ルール)
2. .claude/plans/{PLAN_FILENAME} (あなたの担当プラン)
3. .claude/plans/_progress.md (自分の行を確認)

重要: {KEY_CONTEXT}

権限: ユーザー対話・commit・push・PR・cancelled 判断すべて可。
責務: plan MD ステータス/実行ログ + _progress.md 自分の行 + commit に plan-{PLAN_ID} 含める。
PR/push: {PR_POLICY}。
禁止: 他 worktree 直接編集、main 直接 push。
```

## English version

```
You are a dedicated independent session for plan {PLAN_ID} ({PLAN_FILENAME}). Carry it to done or cancelled.

worktree: .worktrees/{PLAN_ID}/, branch: plan/{PLAN_ID}, base: origin/main.

First read:
1. .claude/plans/INSTRUCTIONS.md (plan operation rules)
2. .claude/plans/{PLAN_FILENAME} (your plan)
3. .claude/plans/_progress.md (find your row)

Context: {KEY_CONTEXT}

Permissions: talk to the user directly, commit, push, open PRs, judge cancelled — all OK.
Responsibilities: update plan MD status/execution log, update your row in _progress.md, include plan-{PLAN_ID} in commits.
PR/push policy: {PR_POLICY}.
Don't: edit other worktrees, push to main directly.
```

## Variant for batch sessions (judging many plans)

```
あなたは plan {BATCH_ID} ({BATCH_FILENAME}) を done まで持っていく一括精査セッションです。

worktree: .worktrees/{BATCH_ID}/、branch: plan/{BATCH_ID}。

担当: {DOMAIN} 系の {N} 件のプランを順次精査し、cancelled / done / ready のいずれかに判定。
worktree 内に {N} 件の plan MD コピー済み、参照可。

各 plan MD の実行ログに判定根拠を必ず残す。終了時に _progress.md の該当行を更新。

PR/push: chore のため PR 不要・push 推奨。
```

## Variant for "implicit done" audit sessions

```
あなたは plan {PLAN_ID} の **監査セッション** です。実装する前に、プランがすでに達成されているかをまず確認してください。

worktree: .worktrees/{PLAN_ID}/、branch: plan/{PLAN_ID}。

監査手順:
1. .claude/plans/{PLAN_FILENAME} の完了条件を読む
2. 現コードを各条件と照合 (git log / grep / file existence / 既存テスト実行)
3. 全部達成済 → "implicit done" 判定、実行ログに証拠 (commit hash, file path) を記録
4. 部分達成 → 残作業を明示してから実装、または "partial done" 判定
5. 達成済だが別経路 → "副次達成 done" 判定、なぜ別経路かを記述
6. 状況変化で不要 → "cancelled" 判定、理由記述

判定根拠は plan MD の実行ログに残す。

PR/push: 監査のみで実装なしの場合 → push 推奨・PR 不要。実装する場合 → 通常の plan PR/push 規約に従う。
```

## Variant for INDEX done sessions

```
あなたは plan {INDEX_ID} INDEX ({INDEX_FILENAME}) を done 判定まで持っていく独立担当セッションです。

worktree: .worktrees/{INDEX_ID}/、branch: plan/{INDEX_ID}。

担当: INDEX 配下の子プラン全てが done/cancelled/blocked になっていることを確認し、本 INDEX を done 判定。

タスク:
1. 配下子プラン {N} 件の最終状態を確認 ({CHILD_IDS})
2. 完了サマリ表を INDEX MD に追加 (ID / Title / status / commit / branch / notes)
3. 残課題フォローアップリストを集約 (実機 E2E / main マージ / deploy など)
4. INDEX MD のステータスを done に更新

新規実装は不要。読んで、まとめて、閉じる。

PR/push: chore のため PR 不要・push 推奨。
```

## Completion summary format (every session must follow)

Every session should emit its completion summary in two sections — one for the user, one for the orchestrator. Include this in your starter prompt:

```
完了時は以下 2 セクション構成で出力すること:

=== ユーザー向け詳細サマリ ===
[このセクションは長くて OK。ユーザーが読んで状況把握する。
 実装内容、検証結果、発見、範囲外メモ、横断観測、PR/commit 情報など]

=== オーケストレーター向け短サマリ (コピペ用) ===
plan {ID} → done|cancelled|blocked
commit: {hash} (pushed: yes|no)
PR: #{N} or none
key: <30 文字程度の要点>
out-of-scope: <0-2 行、横断的なら>
```

```
On completion, emit your summary in two sections:

=== Detailed summary (for the user to read) ===
[This section can be long. The user reads it for situational awareness.
 Cover: what changed, why, what was discovered, residual issues,
 cross-cutting observations, PR / commit info.]

=== Short summary (for the orchestrator — user pastes this) ===
plan {ID} → done|cancelled|blocked
commit: {hash} (pushed: yes|no)
PR: #{N} or none
key: <30-chars take-away>
out-of-scope: <0-2 lines, only if cross-cutting>
```

**Why two sections**: The user wants rich context for their own situational awareness. The orchestrator (a separate Claude Code session managing many of these) wants a short structured update so its context doesn't bloat across ~100 sessions. The user reads the detailed section themselves and pastes only the short section to the orchestrator.

## Tips for writing starter prompts

- **Be concise** — ~200-300 chars works best; the plan MD has the details
- **Be consistent** — sessions should feel "the same shape" across a Wave; helps user navigate multiple conversations
- **Lead with role** — first sentence is "you are X for plan Y"
- **List required reads** — give 2-3 files explicitly
- **One sentence of key context** — only the must-know, not the whole story
- **Permissions + responsibilities + don'ts** — 3 short lines, always in this order
- **PR/push policy** — explicit when not default

Avoid:

- Long context dumps (puts critical info too late)
- Detailed implementation instructions (that's the plan MD's job)
- Ambiguity about scope (sessions feel pressure to expand scope)
