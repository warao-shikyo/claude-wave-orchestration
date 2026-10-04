# STARTER テンプレート（worktree に展開する任務書）

orchestrator が plan ごとに以下の変数を埋めて `.worktrees/{PLAN_ID}/.claude/plans/STARTER.md` として書き出す。セッションマスターは起動後まずこの STARTER.md を読む。

## 変数
- `{PLAN_ID}` … area接頭辞付きID（例 `auth-001`）
- `{PLAN_FILENAME}` … 例 `auth-001-oauth-login.md`
- `{PLAN_TITLE_SHORT}` … 例 `OAuth login`
- `{BASE_BRANCH}` … 例 `integration/latest-known-good`（Wave1のみ `origin/main`）
- `{KEY_CONTEXT}` … 1-2文の固有コンテキスト（直近の動き・依存）

---

# STARTER — plan {PLAN_ID} 担当セッション任務書

あなたは plan **{PLAN_ID}**（{PLAN_FILENAME}「{PLAN_TITLE_SHORT}」）を done または cancelled まで持っていく独立担当セッションです。

## 環境
- worktree: `.worktrees/{PLAN_ID}/`
- branch: `plan/{PLAN_ID}`（base: `{BASE_BRANCH}`）

## 最初に読むもの
1. `.claude/plans/INSTRUCTIONS.md`（plan 運用ルール）
2. `.claude/plans/{PLAN_FILENAME}`（担当 plan・完了条件）
3. `.claude/plans/_progress.md`（自分の行）

## 重要コンテキスト
{KEY_CONTEXT}

## 責務・権限・禁止
- 責務: 実装と **commit まで**（独自判断）。着地はコミット止まり。
- 権限: ユーザーに直接質問可。検証目的のデプロイのみ worktree から可。
- 禁止: push / PR 作成 / main マージ（すべてユーザー判断）、他 worktree 編集、`.gitignore` の `.worktrees/` 削除。
- 委任: 主タスク（実装・ユーザー判断を要するもの）を `Agent`/`Workflow`/`fork` に委任しない。委任は自己完結の読み取り・調査のみ。

## 進め方（この順序で）
1. 実装 → 区切りごとに commit（メッセージに `plan-{PLAN_ID}` を含める）。execution log と `_progress.md` 自分の行をこまめに更新。
2. 完了条件を満たしたら plan を `{PLAN_ID}-<slug>_done.md` にリネームして commit（done はファイル名で表現）。
3. 関連ドキュメント/マニュアルを整合更新（大量読み取りは自己完結サブエージェントに委任可）→ `docs(plan-{PLAN_ID})` で commit。
4. **inbox に完了報告を追記**（下記）。

## inbox 報告（`.claude/plans/inbox.md` に追記）
完了/ブロック/中止時に **append**（上書き禁止）。orchestrator がこれを読んで `_progress.md` 更新・バックログ起票する。

```
## [{PLAN_ID}] {HH:MM} {done|blocked|cancelled}
commit: {hash}（push: no）
verified: unit|integration|manual|deferred
deploy: none|verified-on-deploy|live
updated-docs: <整合したドキュメント、0-3行>
new-issues: <新たな課題、0-3行>
residual: <残課題、0-3行>
key: <30字程度の要点>
```

詳細サマリ（実装内容・検証結果・ターミナル出力の要点）は **このセッションに出力**する（ユーザーが任意に読む）。inbox には上記短サマリだけを書く。

## 権限で拒否される操作（実行依頼）
- auto mode では本番データの読み取り・API キーの使用・外部の有料 API などが拒否される。回避策を自作せず、orchestrator に実行依頼を出す。
- inbox に追記して **commit** する（直接メッセージだけで済ませない。届かないことがある）:

```
## [{PLAN_ID} → orchestrator] 実行依頼
command: <そのまま実行できるコマンド>
count: <本数> / estimate: <費用・時間の見積>
output: .worktrees/{PLAN_ID}/out/<名前>（git 管理外）
approved: <ユーザーが承認したチャットと時刻。無ければ none>
```

- 結果は `out/` に置かれる。待つ間は他の作業を進める。結果の評価と次の判断はあなたとユーザーが行う。

## ユーザー判断が要るとき（judgment）
- inbox に書かず、**あなたが直接このセッションでユーザーに質問**する（orchestrator 経由の中継はしない）。
- ユーザーが不在で即答が無い場合は、`_progress.md` の自分の行を **status: waiting-user** にして待つ。orchestrator が所在をユーザーに通知する（質問内容は流さない＝このセッションで対話する）。

開始してください。
