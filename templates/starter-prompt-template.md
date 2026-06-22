# Session starter prompt template

This is what the orchestrator passes to `launch_claude.py` to launch a session master for one plan.

## Variables to substitute

- `{PLAN_ID}` — the area-prefixed id, e.g. `auth-001` (`<area>-<NNN>`)
- `{PLAN_FILENAME}` — e.g. `auth-001-oauth-login.md`
- `{PLAN_TITLE_SHORT}` — e.g. `OAuth login`
- `{KEY_CONTEXT}` — 1-2 sentences specific to this plan (recent activity, dependencies, etc.)

> **Landing model**: every session master's authority ends at `commit`. push / PR / merge to main are the user's call — so there is no `PR_POLICY` variable to set. Deploying from the worktree for verification only is the one exception.

## Minimal version (≤200 chars equivalent)

```
あなたは plan {PLAN_ID} ({PLAN_FILENAME}) を done または cancelled まで持っていく独立担当セッションです。

worktree: .worktrees/{PLAN_ID}/、branch: plan/{PLAN_ID}、base: integration/latest-known-good（Wave1のみ origin/main）。

最初に .claude/plans/INSTRUCTIONS.md と .claude/plans/{PLAN_FILENAME} と .claude/plans/_progress.md を読んで開始してください。

責務: 実装と commit まで（独自判断）。完了時は plan ファイルを {PLAN_ID}-<slug>_done.md にリネームして commit。commit メッセージに plan-{PLAN_ID} を含める。
権限: ユーザーに直接質問可。
禁止: push / PR 作成 / main へのマージ（すべてユーザー判断）、他 worktree 編集、.gitignore の .worktrees/ 削除。
（検証目的のデプロイのみ worktree から独自判断で可。）

開始してください。
```

## With context (recommended)

```
あなたは plan {PLAN_ID} ({PLAN_FILENAME}) を done/cancelled まで持っていく独立担当セッションです。

worktree: .worktrees/{PLAN_ID}/、branch: plan/{PLAN_ID}、base: integration/latest-known-good（Wave1のみ origin/main）。

最初に読むもの:
1. .claude/plans/INSTRUCTIONS.md (plans 運用ルール)
2. .claude/plans/{PLAN_FILENAME} (あなたの担当プラン)
3. .claude/plans/_progress.md (自分の行を確認)

重要: {KEY_CONTEXT}

責務: 実装と commit まで（独自判断）。plan MD のステータス/実行ログ + _progress.md 自分の行を更新。commit に plan-{PLAN_ID} を含める。
完了: plan ファイルを {PLAN_ID}-<slug>_done.md にリネームして commit（Status 書き換えではなくファイル名で表現）。
権限: ユーザー対話可。検証目的のデプロイのみ worktree から可。
禁止: push / PR / main マージ（すべてユーザー判断）、他 worktree 編集。
```

## English version

```
You are a dedicated independent session for plan {PLAN_ID} ({PLAN_FILENAME}). Carry it to done or cancelled.

worktree: .worktrees/{PLAN_ID}/, branch: plan/{PLAN_ID}, base: integration/latest-known-good (origin/main only on Wave 1).

First read:
1. .claude/plans/INSTRUCTIONS.md (plan operation rules)
2. .claude/plans/{PLAN_FILENAME} (your plan)
3. .claude/plans/_progress.md (find your row)

Context: {KEY_CONTEXT}

Responsibility: implement and **commit** — that's the end of your landing authority. Update plan MD status/execution log and your row in _progress.md. Include plan-{PLAN_ID} in commits.
Done: rename the plan file to {PLAN_ID}-<slug>_done.md and commit (express done by filename, not by a Status flip).
Permissions: talk to the user directly; deploy from the worktree for verification only.
Don't: push / open PRs / merge to main (all the user's call), edit other worktrees.
```

## Variant for batch sessions (judging many plans)

```
あなたは plan {BATCH_ID} ({BATCH_FILENAME}) を done まで持っていく一括精査セッションです。
（{BATCH_ID} は meta- 接頭辞推奨。例 meta-002）

worktree: .worktrees/{BATCH_ID}/、branch: plan/{BATCH_ID}。

担当: {DOMAIN} 系の {N} 件のプランを順次精査し、cancelled / done / ready のいずれかに判定。
worktree 内に {N} 件の plan MD コピー済み、参照可。

各 plan MD の実行ログに判定根拠を必ず残す。done と判定したものはファイル名を _done にリネーム。終了時に _progress.md の該当行を更新。

責務は commit まで。push / PR なし（ユーザー判断）。
```

## Variant for "implicit done" audit sessions

```
あなたは plan {PLAN_ID} の **監査セッション** です。実装する前に、プランがすでに達成されているかをまず確認してください。

worktree: .worktrees/{PLAN_ID}/、branch: plan/{PLAN_ID}。

監査手順:
1. .claude/plans/{PLAN_FILENAME} の完了条件を読む
2. 現コードを各条件と照合 (git log / grep / file existence / 既存テスト実行)
3. 全部達成済 → "implicit done" 判定、実行ログに証拠 (commit hash, file path) を記録し、ファイル名を _done にリネーム
4. 部分達成 → 残作業を明示してから実装、または "partial done" 判定
5. 達成済だが別経路 → "副次達成 done" 判定、なぜ別経路かを記述
6. 状況変化で不要 → "cancelled" 判定（Status と理由を残す。_done にはしない）

判定根拠は plan MD の実行ログに残す。責務は commit まで。push / PR なし。
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
4. INDEX MD のファイル名を {INDEX_ID}-<slug>_done.md にリネームして commit

新規実装は不要。読んで、まとめて、閉じる。責務は commit まで。push / PR なし。
```

## Variant for test-Wave sessions (verification only)

```
あなたは plan {PLAN_ID} の **検証セッション** です。新規実装はしません。

worktree: .worktrees/{PLAN_ID}/、branch: plan/{PLAN_ID}、base: integration/latest-known-good。

対象: {TARGET_PLANS} で出荷されたコードが実際に動くかを検証。
手順:
1. 統合ブランチ上で対象のテスト / E2E を実行
2. 回帰を探す (直近 Wave のホットファイル周辺を重点的に)
3. 発見したバグは新規 plan として提案（完了サマリの new-issues に記載 → オーケストレーターがバックログ起票。軽微かつ範囲内なら修正可）

判定: verified / regressions-found (リスト) / cannot-verify (理由)。根拠は plan MD 実行ログに残す。
done と判定したらファイル名を _done にリネーム。責務は commit まで。push / PR なし。
```

## Completion summary format (every session must follow)

Every session emits its completion summary in two sections — one for the user, one for the orchestrator. Include this in your starter prompt:

```
完了時は以下 2 セクション構成で出力すること:

=== ユーザー向け詳細サマリ ===
[このセクションは長くて OK。ユーザーが読んで状況把握する。
 実装内容、検証結果、ターミナルメッセージの要点(テスト結果/ビルド出力等)、
 発見、新たな課題、残課題、範囲外メモ、commit 情報など]

=== オーケストレーター向け短サマリ (コピペ用) ===
plan {PLAN_ID} → done|cancelled|blocked
commit: {hash} (push: no ※コミットまでが責務)
verified: unit|integration|manual|deferred
deploy: none|verified-on-deploy|live
done-file: {PLAN_ID}-<slug>_done.md
key: <30 文字程度の要点>
new-issues: <新たな課題、0-3 行>
residual: <残課題、0-3 行>
```

```
On completion, emit your summary in two sections:

=== Detailed summary (for the user to read) ===
[This section can be long. The user reads it for situational awareness.
 Cover: what changed, why, what was discovered, terminal-message highlights
 (test results / build output), residual issues, new issues, commit info.]

=== Short summary (for the orchestrator — user pastes this) ===
plan {PLAN_ID} → done|cancelled|blocked
commit: {hash} (push: no — landing authority ends at commit)
verified: unit|integration|manual|deferred
deploy: none|verified-on-deploy|live
done-file: {PLAN_ID}-<slug>_done.md
key: <30-chars take-away>
new-issues: <new issues, 0-3 lines>
residual: <residual work, 0-3 lines>
```

**Why two sections**: The user wants rich context for their own situational awareness. The orchestrator (a separate Claude Code session managing many of these) wants a short structured update so its context doesn't bloat across ~100 sessions. The user reads the detailed section themselves and pastes only the short section to the orchestrator. The orchestrator must file every `new-issues` / `residual` line into the backlog — they are not allowed to be dropped.

## Tips for writing starter prompts

- **Be concise** — ~200-300 chars works best; the plan MD has the details
- **Be consistent** — sessions should feel "the same shape" across a Wave; helps user navigate multiple conversations
- **Lead with role** — first sentence is "you are X for plan Y"
- **List required reads** — give 2-3 files explicitly
- **One sentence of key context** — only the must-know, not the whole story
- **Responsibility + permissions + don'ts** — 3 short lines, always in this order; landing authority ends at `commit`
- **Done = rename to `_done`** — remind the session that done is expressed by filename, not a Status flip

Avoid:

- Long context dumps (puts critical info too late)
- Detailed implementation instructions (that's the plan MD's job)
- Ambiguity about scope (sessions feel pressure to expand scope)
- Implying the session may push / open PRs — it may not
