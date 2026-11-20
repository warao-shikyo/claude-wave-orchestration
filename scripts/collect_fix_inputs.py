"""定時改修プランナーの入力（前回からの差分）を集める

launch_claude.py の `--prompt-script` から呼ばれ、前回の定時改修以降に増えた
改修の種を 1 つの入力ファイルにまとめ、そのパスを 1 行だけ標準出力に出す。
ランチャーはその 1 行を起動プロンプトの末尾に付けて planner を起動する。

使い方:
    python collect_fix_inputs.py <リポジトリ> [--dry-run]   # 集める（ランチャーが呼ぶ）
    python collect_fix_inputs.py <リポジトリ> --ack         # 処理済みにする（planner が完了時に呼ぶ）
    python collect_fix_inputs.py <リポジトリ> --discard-pending  # 未 ack の回を破棄する（手動）

集める入力（すべてリポジトリ相対）:
    - verify の結果   .claude/verify/*.md のうち未処理で、不合格の印があるもの
    - backlog        .claude/plans/_backlog.md の箇条書き（`- ` で始まる行）のうち
                     `planned:` も取り消し線（~~）も付いていないもの。backlog は既読を覚えず
                     印だけで判定する（planner が印を付けなかった行は次回も出る）
    - 全体テストの記録 環境変数 WAVE_FULL_SUITE_LOG で指定したファイルの、前回以降の追記分のうち
                     失敗の印があるもの（未設定なら読まない）

出力と終了コード:
    - 差分あり   : 入力ファイルの相対パスを 1 行出力して 0
    - 差分なし   : 何も出力せず 0（ランチャーは起動しない）
    - 前回が未 ack: 標準エラーに理由を出して 2（同じ種で二重に起票させない）
    - その他の異常: 例外のまま非 0

状態は .claude/scheduled-fix/ に置く（中に `*` だけの .gitignore を作るので追跡されない）。
verify と全体テストの記録は、planner が --ack したときだけ処理済みにする。planner が途中で落ちたら、
--discard-pending で破棄すれば次回に同じ種がもう一度出る。
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

STATE_DIR = Path(".claude/scheduled-fix")
STATE_FILE = STATE_DIR / "state.json"
VERIFY_DIR = Path(".claude/verify")
BACKLOG_FILE = Path(".claude/plans/_backlog.md")
SUITE_LOG_ENV = "WAVE_FULL_SUITE_LOG"

# verify・全体テストの記録で「失敗」とみなす印（大文字小文字を区別しない）
FAIL_PATTERN = re.compile(r"\bfail(ed|ure|s)?\b|不合格|verify-failed|\bFAILED\b|\bERROR\b|赤", re.IGNORECASE)
# 「fail 0」「0 failed」のように失敗 0 件を表す書き方は失敗とみなさない
ZERO_FAIL_PATTERN = re.compile(r"\bfail(ed|s)?\s*[:=]?\s*0\b|\b0\s+fail(ed|s)?\b", re.IGNORECASE)


def empty_state():
    return {"seen": {"verify": [], "suite_offset": 0}, "pending": None}


def load_state(repo):
    path = repo / STATE_FILE
    if not path.exists():
        return empty_state()
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(repo, state):
    state_dir = repo / STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    ignore = state_dir / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n", encoding="utf-8")
    (repo / STATE_FILE).write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def has_failure(text):
    """失敗の印があるか。失敗 0 件の書き方を除いてから判定する。"""
    return bool(FAIL_PATTERN.search(ZERO_FAIL_PATTERN.sub("", text)))


def collect_verify(repo, seen):
    """未処理の verify 結果を返す（considered: 処理済みにする全件, failed: 入力に載せるもの）。"""
    verify_dir = repo / VERIFY_DIR
    if not verify_dir.is_dir():
        return [], []
    considered, failed = [], []
    for path in sorted(verify_dir.glob("*.md")):
        if path.name in seen:
            continue
        considered.append(path.name)
        if has_failure(path.read_text(encoding="utf-8")):
            failed.append(path.relative_to(repo).as_posix())
    return considered, failed


def collect_backlog(repo):
    path = repo / BACKLOG_FILE
    if not path.exists():
        return []
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("- "):
            continue
        if "planned:" in line or line[2:].lstrip().startswith("~~"):
            continue
        items.append(line.strip())
    return items


def collect_suite(repo, offset):
    """全体テストの記録の追記分を返す（new_offset, 失敗の印がある追記本文 or None, 記録のパス）。"""
    rel = os.environ.get(SUITE_LOG_ENV)
    if not rel:
        return offset, None, None
    path = repo / rel
    if not path.exists():
        raise FileNotFoundError(f"{SUITE_LOG_ENV} のファイルがありません: {path}")
    data = path.read_bytes()
    if len(data) < offset:
        raise RuntimeError(
            f"全体テストの記録が前回より短くなっています（{len(data)} < {offset} バイト）: {path}。"
            f"書き換えた場合は {STATE_FILE} の suite_offset を直してください"
        )
    added = data[offset:].decode("utf-8")
    return len(data), (added if has_failure(added) else None), Path(rel).as_posix()


def write_inputs(repo, stamp, verify_failed, backlog_items, suite_text, suite_rel):
    rel = (STATE_DIR / f"inputs-{stamp}.md").as_posix()
    lines = [
        f"# 定時改修の入力 {stamp}",
        "",
        "前回の定時改修以降に増えた改修の種。各項目を session-planner の定時改修モードで扱う。",
        f"完了したら `python \"{Path(__file__).resolve().as_posix()}\" \"{repo.as_posix()}\" --ack` を実行する。",
        "",
    ]
    if verify_failed:
        lines += ["## verify の不合格", ""] + [f"- `{p}`" for p in verify_failed] + [""]
    if backlog_items:
        lines += ["## backlog の未起票項目（`.claude/plans/_backlog.md`）", ""]
        lines += backlog_items + [""]
    if suite_text is not None:
        lines += [f"## 全体テストの記録の追記分（`{suite_rel}`）", "", "```", suite_text.rstrip("\n"), "```", ""]
    (repo / rel).write_text("\n".join(lines), encoding="utf-8")
    return rel


def cmd_collect(repo, dry_run):
    state = load_state(repo)
    if state["pending"] is not None:
        print(
            f"前回の定時改修（{state['pending']['inputs']}）が ack されていません。"
            "planner が動いていないか確かめ、終わっていれば --ack、落ちていれば --discard-pending を実行してください",
            file=sys.stderr,
        )
        return 2
    seen = state["seen"]
    considered_verify, verify_failed = collect_verify(repo, set(seen["verify"]))
    backlog_items = collect_backlog(repo)
    suite_offset, suite_text, suite_rel = collect_suite(repo, seen["suite_offset"])

    count = len(verify_failed) + len(backlog_items) + (1 if suite_text is not None else 0)
    print(
        f"定時改修の差分: verify 不合格 {len(verify_failed)} 件 / backlog {len(backlog_items)} 件 / "
        f"全体テスト {'失敗あり' if suite_text is not None else ('失敗なし' if suite_rel else '未設定')}",
        file=sys.stderr,
    )
    if dry_run:
        if count:
            print((STATE_DIR / "inputs-<日時>.md").as_posix())
        return 0
    if count == 0:
        # 起票の種は無いが、合格の verify と全体テストの追記は読み終えたので進めておく
        seen["verify"] += considered_verify
        seen["suite_offset"] = suite_offset
        save_state(repo, state)
        return 0

    save_state(repo, state)  # 状態ディレクトリと .gitignore を先に用意する
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    rel = write_inputs(repo, stamp, verify_failed, backlog_items, suite_text, suite_rel)
    state["pending"] = {
        "inputs": rel,
        "verify": considered_verify,
        "suite_offset": suite_offset,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    save_state(repo, state)
    print(rel)
    return 0


def cmd_ack(repo):
    state = load_state(repo)
    pending = state["pending"]
    if pending is None:
        print("ack する回がありません（pending なし）", file=sys.stderr)
        return 1
    state["seen"]["verify"] += pending["verify"]
    state["seen"]["suite_offset"] = pending["suite_offset"]
    state["pending"] = None
    save_state(repo, state)
    print(f"処理済みにしました: {pending['inputs']}")
    return 0


def cmd_discard(repo):
    state = load_state(repo)
    if state["pending"] is None:
        print("破棄する回がありません（pending なし）", file=sys.stderr)
        return 1
    inputs = state["pending"]["inputs"]
    state["pending"] = None
    save_state(repo, state)
    print(f"未 ack の回を破棄しました（次回に同じ種がもう一度出ます）: {inputs}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="定時改修プランナーの入力（前回からの差分）を集める")
    parser.add_argument("repo", help="リポジトリのルート（本流。worktree ではない）")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="集計を表示するだけで状態を書かない")
    group.add_argument("--ack", action="store_true", help="pending の回を処理済みにする")
    group.add_argument("--discard-pending", action="store_true", help="pending の回を破棄する")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        raise FileNotFoundError(f"git リポジトリのルートではありません: {repo}")
    if args.ack:
        return cmd_ack(repo)
    if args.discard_pending:
        return cmd_discard(repo)
    return cmd_collect(repo, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
