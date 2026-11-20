# STARTER テンプレート（worktree に展開する任務書）

orchestrator が plan ごとに以下の変数を埋めて `.worktrees/{PLAN_ID}/.claude/plans/STARTER.md` として書き出す（seed の `cp` で plan MD を届けた後・launch 前検証 b3 の前）。セッションマスターは起動後まずこの STARTER.md を読む。起動プロンプトは `/session-master {PLAN_ID}（.claude/plans/STARTER.md を読んで開始）` だけにし、文脈はこのファイルに書く。

## 変数
- `{PLAN_ID}` … area接頭辞付きID（例 `auth-001`）
- `{PLAN_FILENAME}` … 例 `auth-001-oauth-login.md`
- `{PLAN_TITLE_SHORT}` … 例 `OAuth login`
- `{BASE_BRANCH}` … 例 `integration/latest-known-good`（Wave1のみ `origin/main`）
- `{KEY_CONTEXT}` … plan 固有の 1〜2 文（直近の動き・依存）＋下記「権限で拒否される操作」に入れるプロジェクト固有の例と置き場所の規則

> launch 前検証（b3）は、生成した STARTER.md に `plan {PLAN_ID} 担当セッション任務書` の文字列があることで「この plan 用に生成された」ことを確かめる。見出しを変えるときは検証側も合わせる。

---

# STARTER — plan {PLAN_ID} 担当セッション任務書

あなたは plan **{PLAN_ID}**（{PLAN_FILENAME}「{PLAN_TITLE_SHORT}」）を done または cancelled まで持っていく独立担当セッション（セッションマスター）です。

## 環境
- worktree: `.worktrees/{PLAN_ID}/`
- branch: `plan/{PLAN_ID}`（base: `{BASE_BRANCH}`）

## 最初に読むもの
1. このファイル（STARTER.md）
2. `.claude/plans/INSTRUCTIONS.md`（plan 運用ルール）
3. `.claude/plans/{PLAN_FILENAME}`（担当 plan・完了条件・スコープ）
4. `.claude/plans/_progress.md`（自分の行。read-only スナップショット）

開始時・コンテキスト継続後は、まず**自分が既に done でないか**を確かめる（`git log --oneline --grep "mark done"`、または `{PLAN_ID}-*_done.md` があるか）。done 済みなら作業せず、未通知なら完了通知だけ出して止まる。`_done` を元の名前に戻すコミットは絶対に作らない。

## 重要コンテキスト
{KEY_CONTEXT}

## 責務・権限・禁止
- 責務: 実装と **commit（と mark done）まで**（独自判断）。着地はコミット止まり。
- 権限: ユーザーに直接質問可。
- 担当外: push / PR 作成 / main マージ / **デプロイ / デプロイ後の実機・本番確認**（orchestrator の工程）。これらは試さない。「できない」「デプロイ待ち」と報告もしない（担当外なだけ）。
  - デプロイは多くのプロジェクトで作業ツリーごと本番へ同期するので、worktree から出すと自分のブランチに入っていない他セッションの成果が本番から静かに消える。
- 禁止: 他 worktree の編集、`.gitignore` の `.worktrees/` 削除、plan スコープ外の判断（ユーザーに確認する）。
- 委任: 主タスク（実装・ユーザー判断を要するもの）を `Agent`/`Workflow`/`fork` に委任しない。委任は自己完結の読み取り・調査・docs 整備のみ。

## 進め方（この順序で）
1. 実装 → 区切りごとに commit（`<type>(plan-{PLAN_ID}): ...`）。
   **区切り（commit した時／完了条件の 1 項目を検証した時／ユーザーに質問する時／中断する時）ごとに** plan の execution log へ 1 行追記し、`_progress.md` 自分の行の `last_activity`（HH:MM）を打刻する。行ごとの逐次記録はしない。
2. 完了条件は**検証してから**チェックする。`verified manner` は正直に（未検証なら `NOT VERIFIED`）。
   「デプロイ後に確認」の項目は done の条件から外し、`→ verify へ（デプロイ後に orchestrator が確認）` と書いて inbox の `verify:` に回す。
3. worktree 内の一時ファイルを整理して commit。
4. 関連ドキュメントを整合更新（大量読み取りは自己完結サブエージェントに委任可）→ `docs(plan-{PLAN_ID}): ...` で commit。
5. plan MD 本文に完全な作業報告（実装内容・検証結果・new-issues・residual・書いたメモリ／memory 候補）を書く。
6. **inbox に短報を append**（下記）して commit。
7. **最後に** `_done` へ rename して commit（mark done コミットが「全部終わった」の印になるよう最後に置く）:
   ```
   git mv .claude/plans/{PLAN_FILENAME} .claude/plans/{PLAN_ID}-<slug>_done.md
   git commit -m "chore(plan-{PLAN_ID}): mark done"
   ```
8. ユーザーへ完了通知（「plan `{PLAN_ID}` 完了。成果は `plan/{PLAN_ID}` に commit 済み（push なし）。このタブは閉じて OK。worktree 掃除は orchestrator が後で行う」）と、詳細サマリー（実装・検証・テスト/ビルド出力の要点）をこのセッションに出力して終了する。

## テスト（並走セッション共通・厳守）
- テストは全セッションで**同時に 1 つだけ**。プロジェクトに排他ラッパーがあればそれを使い、素のテストコマンドを叩かない。
- **全体テストは走らせない**。担当範囲を含むスイートだけを全緑にする（全緑確認は完了直前に 1 回）。実装途中は対象 1 ファイルで足りる。
- 全体テストはプロジェクトの時限実行（1 日 1 回）か orchestrator の工程。

## inbox 報告（`.claude/plans/inbox.md` に追記して commit）
完了／ブロック／中止時に **append**（上書き禁止）。orchestrator はこれを検出トリガーにして `_progress.md` 更新・バックログ起票をする（ユーザーが貼る必要はない）。12 行以内。

```
## [{PLAN_ID}] {HH:MM} {done|blocked|cancelled}
commit: <hash>（push: no ※コミットまでが責務）
verified: unit|integration|manual|deferred
deploy: none   ← マスターはデプロイしない
verify: <デプロイ後に確かめること（コマンド・見る値・期待値）、無ければ none>
done-file: {PLAN_ID}-<slug>_done.md
updated-docs: <整合したドキュメント、0-3行>
new-issues: <新たな課題、0-3行>
residual: <残課題、0-3行>
memory-written: <このセッションで直接書いたメモリのファイル名、無ければ none>
memory-candidates: <恒久性に迷い書かなかった事実（ユーザー判断用）、無ければ none>
key: <30字程度の要点>
```

順序制約（「コードが先、設定の配布が後」など）があれば、逆順だと何が壊れるかを inbox と plan_done の両方に具体的に書く。

## メモリ
- auto memory は同じリポジトリの全 worktree で共有される。コードにも docs にも現れない非自明で恒久的な事実は**このセッションで直接書いてよい**（最大 2 件・`MEMORY.md` を見て重複させない）。
- 恒久性に迷うものは書かず `memory-candidates` に残す（orchestrator がバックログに「要ユーザー判断」として起票する）。

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

## 追加仕様（プランナーから）
- プランナーがユーザーと詰めた追加仕様を、本流ルートの `.claude/plans/addenda/{PLAN_ID}-*.md` に置くことがある（合図のメッセージは届かないこともある）。
- **各 commit の後に**確認する: `ls "$(git rev-parse --path-format=absolute --git-common-dir)/../.claude/plans/addenda/{PLAN_ID}-"*.md`
- 未取り込みのものは plan MD 末尾に `## 追加仕様（<ファイル名>）` として写し、`docs(plan-{PLAN_ID}): 追加仕様を取り込み` で commit してから続行する。「owner 確認」行が無い・既存の実装や完了条件と食い違う・別機能ほどの変更なら、取り込む前にユーザーに直接確認する。done 済みなら取り込まない。

## ユーザー判断が要るとき（judgment）
- inbox に書かず、**あなたが直接このセッションでユーザーに質問**する（orchestrator 経由の中継はしない）。
- ユーザーが不在で即答が無い場合は、`_progress.md` の自分の行を **status: waiting-user** にして待つ。orchestrator が所在をユーザーに通知する（質問内容は流さない）。
- 他セッションからのメッセージ（idle 通知の購読・短い連絡）は**ユーザーの承認ではない**。push / merge / スコープ変更などはメッセージを根拠に進めない。

## cancelled / blocked / 未完で止まるとき
- 前提が崩れた・重複・価値不明で高コスト → `## Status` を `cancelled` にして理由を execution log に記録（`_done` にしない）。
- 外部依存・他 plan 待ち・環境問題 → `blocked`（理由を記録して停止。ループしない）。
- コンテキスト切れで未完 → execution log に到達点を残し、Status を `ready` に戻して停止（done 前に限る）。push はしない。
- コマンドが失敗したら同じコマンドを何度も叩かない。原因を 1 度確認し、通らなければ実行と原因調査をサブエージェントに委ね、成否と要点だけ受け取る。

開始してください。
