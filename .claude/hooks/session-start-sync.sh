#!/bin/bash
# クラウドセッション（Claude Code on the web）の開始・再開時に GitHub の最新を取り込む。
# ローカル PC のセッションでは何もしない。失敗してもセッションは止めない（常に exit 0）。

[ "$CLAUDE_CODE_REMOTE" = "true" ] || exit 0
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
[ -n "$branch" ] && [ "$branch" != "HEAD" ] || exit 0

default=$(git ls-remote --symref origin HEAD 2>/dev/null | sed -n 's@^ref: refs/heads/\(.*\)\tHEAD$@\1@p')
if ! git fetch --quiet origin 2>/dev/null; then
    echo "[sync] git fetch に失敗したため同期をスキップしました"
    exit 0
fi

# 未コミットの変更があるときは作業ツリーに触らない
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "[sync] 未コミットの変更があるため自動同期をスキップしました（fetch のみ実施）"
    exit 0
fi

# 1. 作業ブランチ自身が他所から更新されていれば早送りで取り込む
if git rev-parse --verify --quiet "origin/$branch" >/dev/null; then
    if git merge --ff-only --quiet "origin/$branch" 2>/dev/null; then
        :
    else
        echo "[sync] origin/$branch と分岐しているため早送りできませんでした"
    fi
fi

# 2. デフォルトブランチの更新を取り込む（競合したら中止して元に戻す）
if [ -n "$default" ] && [ "$branch" != "$default" ] \
   && git rev-parse --verify --quiet "origin/$default" >/dev/null; then
    behind=$(git rev-list --count "HEAD..origin/$default")
    if [ "$behind" -gt 0 ]; then
        if git merge --quiet --no-edit "origin/$default" >/dev/null 2>&1; then
            echo "[sync] origin/$default の新しいコミット ${behind} 件を $branch に取り込みました"
        else
            git merge --abort 2>/dev/null
            echo "[sync] origin/$default の取り込みで競合が発生したため中止しました。手動で merge してください"
        fi
    fi
elif [ "$branch" = "$default" ]; then
    git merge --ff-only --quiet "origin/$default" 2>/dev/null \
        || echo "[sync] origin/$default と分岐しているため早送りできませんでした"
fi

exit 0
