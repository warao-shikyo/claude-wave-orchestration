# Session starter prompt template

What the orchestrator passes to `launch_claude.py` as the first prompt of a session master.

## Standard form (with the session-master skill)

Keep the launch prompt to one line. Everything plan-specific goes into `STARTER.md` (generated from [starter-md-template.md](starter-md-template.md) and seeded into the worktree before launch):

```bash
MSYS_NO_PATHCONV=1 python launch_claude.py "$(pwd -W)/.worktrees/${PLAN_ID}" \
  --role master --plan-id "${PLAN_ID}" --task "${PLAN_TITLE}" \
  "/session-master ${PLAN_ID}（.claude/plans/STARTER.md を読んで開始）"
```

- `MSYS_NO_PATHCONV=1` is mandatory from Git Bash: otherwise MSYS rewrites the leading `/` into `C:/Program Files/Git/session-master …` and the slash command never resolves. Use `$(pwd -W)` (`C:/...` form) with it, since `$(pwd)` (`/c/...`) is no longer converted.
- **No backticks in the launch prompt** — bash executes them. Put long context in STARTER.md.
- On macOS / Linux drop `MSYS_NO_PATHCONV=1` and use `$(pwd)`.

## Without the skill (plain prompt)

If you don't install the session-master skill, put the essentials in the prompt itself and still keep the details in STARTER.md.

### Variables

- `{PLAN_ID}` — the area-prefixed id, e.g. `auth-001`
- `{PLAN_FILENAME}` — e.g. `auth-001-oauth-login.md`
- `{KEY_CONTEXT}` — 1-2 sentences specific to this plan

> **Landing model**: a session master's authority ends at `commit` (and `mark done`). push / PR / merge to main / deploy are not its job — post-deploy checks go into the inbox `verify:` line. There is no per-plan override.

### Minimal version (Japanese)

```
あなたは plan {PLAN_ID} ({PLAN_FILENAME}) を done または cancelled まで持っていく独立担当セッションです。
最初に .claude/plans/STARTER.md を読み、そこに書かれた順に INSTRUCTIONS.md・担当 plan・_progress.md を読んで開始してください。
責務: 実装と commit まで。完了時は inbox に短報を追記して commit し、最後に plan を {PLAN_ID}-<slug>_done.md にリネームして commit。
担当外: push / PR / main マージ / デプロイ（デプロイ後の確認は inbox の verify: に書く）。禁止: 他 worktree 編集。
```

### English version

```
You are a dedicated session for plan {PLAN_ID} ({PLAN_FILENAME}). Carry it to done or cancelled.
First read .claude/plans/STARTER.md, then INSTRUCTIONS.md, your plan MD and _progress.md as it says.
Responsibility: implement and commit. On completion append a short report to the inbox and commit, then rename the plan to {PLAN_ID}-<slug>_done.md and commit.
Not your job: push / PR / merge to main / deploy (write post-deploy checks as verify: in the inbox). Don't edit other worktrees.
```

## Variants (put the variant text into STARTER.md's `{KEY_CONTEXT}`)

### Batch session (judging many plans)

```
この plan は一括精査セッション（{BATCH_ID}、meta- 接頭辞推奨。例 meta-002）です。
担当: {DOMAIN} 系の {N} 件のプランを順次精査し、cancelled / done / ready のいずれかに判定。
worktree 内に {N} 件の plan MD をコピー済み。各 plan MD の実行ログに判定根拠を必ず残す。
done と判定したものはファイル名を _done にリネーム。
```

### "Implicit done" audit session

```
この plan は監査セッションです。実装する前に、プランがすでに達成されているかをまず確認してください。
1. 完了条件を読む 2. 現コードと照合（git log / grep / ファイルの有無 / 担当範囲のテスト）
3. 全部達成済 → implicit done（証拠の commit hash・パスを実行ログに記録し _done にリネーム）
4. 部分達成 → 残作業を明示してから実装、または partial done
5. 別経路で達成 → 副次達成 done（なぜ別経路かを記述）
6. 状況変化で不要 → cancelled（Status と理由。_done にしない）
```

### INDEX done session

```
この plan は INDEX（{INDEX_ID}）を閉じるセッションです。新規実装は不要。
配下の子プラン {N} 件（{CHILD_IDS}）の最終状態を確認し、完了サマリ表（ID / Title / status / commit / branch / notes）と
残課題リストを INDEX MD に追加して、INDEX MD を _done にリネームする。
```

### Test-Wave session (verification only)

```
この plan は検証セッションです。新規実装はしません。
対象: {TARGET_PLANS} で出荷されたコードが動くかを統合ブランチ上で検証し、回帰を探す。
テストは排他ラッパー経由で 1 本ずつ・担当範囲を絞る（全体テストは時限実行に任せる）。
発見したバグは new-issues に新規 plan として提案（軽微かつ範囲内なら修正可）。
判定: verified / regressions-found（リスト） / cannot-verify（理由）。
```

## Completion report (every session)

Sessions do **not** emit a "paste this to the orchestrator" block any more. They:

1. append the short report to `.claude/plans/inbox.md` and commit it (format in [INSTRUCTIONS.md](INSTRUCTIONS.md#inbox-short-report-append-to-claudeplansinboxmd)) — the orchestrator picks it up on its patrol;
2. print a detailed summary (what changed, verification, test/build output highlights, discoveries) in their own terminal for the user to read whenever they like.

The orchestrator must file every `new-issues` / `residual` / `memory-candidates` line into the backlog — none may be dropped.

## Tips

- **Be concise** — the launch prompt is one line; STARTER.md carries the context, the plan MD carries the details
- **Lead with role** — "you are X for plan Y"
- **One or two sentences of key context** in STARTER.md — only the must-know, plus the project's list of operations denied in auto mode and where outputs must go
- **Done = rename to `_done`, last** — the mark-done commit is the "all finished" latch

Avoid:

- Long context dumps in the launch prompt (critical info arrives too late; backticks break it)
- Detailed implementation instructions (the plan MD's job)
- Implying the session may push / open PRs / deploy — it may not
