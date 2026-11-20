"""新しい Claude Code セッションを独立したターミナル（タブ）で起動する

Windows + Windows Terminal (`wt`) 向け。macOS（iTerm2）・tmux にも最低限対応する。

使い方:
    python launch_claude.py <プロジェクトパス> [ランチャーオプション] [claude に渡す引数...]

ランチャーオプション（すべて任意。1つも付けなければ素の起動）:
    --role orchestrator|master|planner|single
        役割。タブ名の頭文字（O/M/P/S）とタブ色を決める。
    --task "<任務要約>"
        タブ名の末尾に付ける任務要約（全角15字程度で切る）。plan タイトルから作る。
        --role を省略して --task だけ付けると single 扱い。
    --plan-id <id>
        タブ名の <プロジェクト名>/<plan-id> 部分。省略時、パスが
        <project>/.worktrees/<id> ならそこから自動で取る。
    --bg
        ターミナルを開かず `claude --bg --name <タブ名>` でバックグラウンド起動する（opt-in）。
        操作は `claude agents` / `claude attach <id>`、停止は `claude stop <id>`。
        Remote Control 一覧に出るかは環境で確かめてから使う。
    --no-remote-control
        `--remote-control <タブ名>` を付けない（Remote Control を使わない環境向け）。
    --dry-run
        起動せず、実行するコマンドとタブ名を表示するだけ。

タブ名 = Remote Control 名 = `--name` = `<役割頭文字>:<プロジェクト名>[/<plan-id>] <任務要約>`
    例: M:myapp/auth-001 OAuthログイン追加

相対パスは「このスクリプトを実行した cwd」基準で解決する（オーケストレーターは
プロジェクトルートから `.worktrees/<id>` を渡す想定）。

例:
    python launch_claude.py ../myapp --role orchestrator --task "バックログ消化" \\
        --effort medium "/loop /session-orchestrator バックログ消化"
    python launch_claude.py ../myapp --role planner --task "請求の二重送信" \\
        "/session-planner 請求画面で二重送信が起きる"
    MSYS_NO_PATHCONV=1 python launch_claude.py "$(pwd -W)/.worktrees/auth-001" --role master \\
        --plan-id auth-001 --task "OAuthログイン追加" \\
        "/session-master auth-001（.claude/plans/STARTER.md を読んで開始）"

🔴 Git Bash から `/loop ...` `/session-master ...` のように先頭がスラッシュの引数を渡すときは
   `MSYS_NO_PATHCONV=1` を必ず付ける。付けないと MSYS のパス変換で
   `C:/Program Files/Git/session-master ...` に化け、スラッシュコマンドとして解決されない。

起動記録:
    起動ごとに ~/.claude/wave-launch-log.jsonl へ 1 行追記する（WAVE_LAUNCH_LOG で変更可）。
    セッション単位の費用の突き合わせと、生存確認スクリプトのデータ源に使う。

この雛形版に無いもの（運用側で用意する）:
    - 二重起動の防止（稼働中の claude プロセスを列挙して同じタブ名・同じ plan のマスターを止める）。
      プロセス列挙ツールに依存するため雛形には含めない。起動前に同じ plan のマスターが
      生きていないことを確かめること（同一 worktree に 2 セッションが同居するとコミットが競合する）。
    - 伝言板（ユーザー待ちの一覧）への記録。
"""
import json
import os
import shutil
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_JSON_PATH = Path.home() / ".claude.json"
# ~/.claude.json の同時書き込み（連続起動）に備えた再試行の間隔（秒）
LOCK_RETRY_DELAYS = [1, 2, 4, 8]
# 起動記録の置き場所（WAVE_LAUNCH_LOG で変更可）。1 起動 1 行の JSONL
LAUNCH_LOG_PATH = Path(
    os.environ.get("WAVE_LAUNCH_LOG", str(Path.home() / ".claude" / "wave-launch-log.jsonl"))
)
# wt で開くプロファイル名（任意）。設定したときだけ `-p <名前>` を付ける。
# タブ名は --title、色は --tabColor で渡すのでプロファイルには依存しない。
WT_PROFILE_ENV = "WAVE_WT_PROFILE"

# 役割ごとのタブ名頭文字とタブ色（Windows Terminal の --tabColor）。
# 色は「状態」ではなく「役割」を表す（状態で色を変えない）。
ROLES = {
    "orchestrator": ("O", "#8E44AD"),  # 紫
    "master": ("M", "#2E86DE"),        # 青
    "planner": ("P", "#27AE60"),       # 緑
    "single": ("S", "#7F8C8D"),        # 灰
}

# 任務要約の最大表示幅（全角1字=2、半角1字=1 で数える。30 = 全角15字）
TASK_MAX_WIDTH = 30

LAUNCHER_FLAGS_WITH_VALUE = ("--role", "--task", "--plan-id")
LAUNCHER_FLAGS_BOOL = ("--bg", "--dry-run", "--no-remote-control")

MCP_APPROVAL_LIST_KEYS = ("enabledMcpjsonServers", "disabledMcpjsonServers")
MCP_APPROVAL_FLAG_KEY = "enableAllProjectMcpServers"

TRUSTED_ENTRY = {
    "allowedTools": [],
    "mcpContextUris": [],
    "enabledMcpjsonServers": [],
    "disabledMcpjsonServers": [],
    "hasTrustDialogAccepted": True,
    "projectOnboardingSeenCount": 0,
    "hasClaudeMdExternalIncludesApproved": False,
    "hasClaudeMdExternalIncludesWarningShown": False,
}


class UsageError(Exception):
    """引数の誤り。"""


def usage_text():
    return (
        "使い方: python launch_claude.py <プロジェクトパス> "
        "[--role orchestrator|master|planner|single] [--task \"<任務要約>\"] "
        "[--plan-id <id>] [--bg] [--no-remote-control] [--dry-run] [claude に渡す引数...]\n"
        "例: python launch_claude.py .worktrees/auth-001 --role master --task \"OAuthログイン追加\" "
        "\"/session-master auth-001（.claude/plans/STARTER.md を読んで開始）\""
    )


def split_launcher_args(argv):
    """argv（プロジェクトパスより後ろ）からランチャー自身のオプションを抜き出す。

    argparse を使わないのは、claude に渡す引数（--effort medium や "/loop ..." の
    プロンプト）の順序と中身をそのまま保つため。
    """
    opts = {"role": None, "task": None, "plan_id": None,
            "bg": False, "dry_run": False, "no_remote_control": False}
    rest = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        name, eq, inline_value = arg.partition("=")
        if name in LAUNCHER_FLAGS_WITH_VALUE:
            if eq:
                value = inline_value
            else:
                if i + 1 >= len(argv):
                    raise UsageError(f"{name} には値が必要です")
                value = argv[i + 1]
                i += 1
            opts[name[2:].replace("-", "_")] = value
        elif arg in LAUNCHER_FLAGS_BOOL:
            opts[arg[2:].replace("-", "_")] = True
        else:
            rest.append(arg)
        i += 1
    if opts["role"] is not None and opts["role"] not in ROLES:
        raise UsageError(f"--role は {', '.join(ROLES)} のいずれか: {opts['role']}")
    return opts, rest


def display_width(text):
    """全角（East Asian Wide/Fullwidth）を 2、それ以外を 1 として幅を数える。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def truncate_task(text, max_width=TASK_MAX_WIDTH):
    """任務要約を表示幅 max_width までに切る（切ったら末尾に … を付ける）。"""
    # 改行・タブは1行のタブ名に入れない。';' は wt がコマンド区切りとして解釈するので全角にする
    text = " ".join(text.split()).replace(";", "；")
    if display_width(text) <= max_width:
        return text
    out = []
    width = 0
    for ch in text:
        w = display_width(ch)
        if width + w > max_width - 1:  # … の分（幅1）を残す
            break
        out.append(ch)
        width += w
    return "".join(out).rstrip() + "…"


def derive_project_and_plan(project_path):
    """パスから (プロジェクト名, plan-id or None) を推定する。

    <project>/.worktrees/<id>[/...] なら (<project>, <id>)。それ以外はディレクトリ名。
    """
    parts = project_path.parts
    if ".worktrees" in parts:
        idx = parts.index(".worktrees")
        if 0 < idx and idx + 1 < len(parts):
            return parts[idx - 1], parts[idx + 1]
    return project_path.name or "claude", None


def build_title(project_path, role=None, task=None, plan_id=None):
    """タブ名（= Remote Control 名 = --name）を組み立てる。

    役割も任務も指定されていなければディレクトリ名だけを返す。
    """
    if role is None and task is None:
        return project_path.name or "claude"
    role = role or "single"
    project, derived_plan = derive_project_and_plan(project_path)
    plan = plan_id or derived_plan
    head = f"{ROLES[role][0]}:{project}"
    if plan:
        head += f"/{plan}"
    if task:
        summary = truncate_task(task)
        if summary:
            return f"{head} {summary}"
    return head


def worktree_root(project_path):
    """<project>/.worktrees/<id>[/...] なら <project>（本流ルート）を返す。それ以外は None。

    worktree で起動するマスターは cwd が worktree なので、本流ルートにしか無いもの
    （.venv・秘密ファイルなど .gitignore 対象、main の .claude/plans/addenda/）が作業
    ディレクトリの外になり、読み書きが確認・拒否で止まる。cwd は worktree のまま
    （git の向き先・書き込み先の安全を保つ）、本流ルートだけを --add-dir で足す。
    """
    parts = project_path.parts
    if ".worktrees" in parts:
        idx = parts.index(".worktrees")
        if 0 < idx and idx + 1 < len(parts):
            return Path(*parts[:idx])
    return None


def _read_settings(path):
    """settings.local.json を読む。無ければ None。壊れていれば ValueError をそのまま上げる。"""
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} の中身がオブジェクトではありません")
    return data


def inherit_mcp_approval(main_root, worktree):
    """本流の .claude/settings.local.json にある .mcp.json の承認を worktree に引き継ぐ。

    worktree ごとに「MCP サーバーを使うか」のダイアログが出て、Remote Control からは
    見えずに起動が止まるため。本流でユーザーが既にした承認・拒否だけを写す（新たに
    承認を増やさない）。worktree 側に既にある値は消さない。戻り値: 書き込んだら True。
    """
    src_path = Path(main_root) / ".claude" / "settings.local.json"
    dst_path = Path(worktree) / ".claude" / "settings.local.json"
    try:
        src = _read_settings(src_path)
        dst = _read_settings(dst_path)
    except ValueError as e:
        print(f"警告: MCP の承認を引き継げませんでした（{e}）。起動後に MCP の確認ダイアログが出ることがあります",
              file=sys.stderr)
        return False
    if src is None:
        return False
    dst = {} if dst is None else dst
    changed = False
    for key in MCP_APPROVAL_LIST_KEYS:
        values = src.get(key)
        if not isinstance(values, list) or not values:
            continue
        current = dst.get(key) if isinstance(dst.get(key), list) else []
        merged = current + [v for v in values if v not in current]
        if merged != dst.get(key):
            dst[key] = merged
            changed = True
    if MCP_APPROVAL_FLAG_KEY in src and MCP_APPROVAL_FLAG_KEY not in dst:
        dst[MCP_APPROVAL_FLAG_KEY] = src[MCP_APPROVAL_FLAG_KEY]
        changed = True
    if not changed:
        return False
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_text(json.dumps(dst, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"MCP の承認を本流から引き継ぎ: {dst_path}")
    return True


def register_trust(resolved_path):
    """指定パスを信頼済みとして ~/.claude.json に登録する。

    Claude Code はバージョンにより参照キーの形式（バックスラッシュ/スラッシュ）が
    異なるので、両形式で登録する。~/.claude.json が無い PC（Claude Code 未起動）は
    作らずにスキップする（初回は手動で一度起動して信頼ダイアログを承認する）。
    連続起動で他のランチャーが書き込み中のときは間隔を空けて再試行する。
    """
    last_error = None
    for delay in [0] + LOCK_RETRY_DELAYS:
        if delay:
            time.sleep(delay)
        try:
            if not CLAUDE_JSON_PATH.exists():
                print(f"~/.claude.json が未作成のため信頼登録をスキップ: {CLAUDE_JSON_PATH}")
                print("  初回は対象ディレクトリで claude を一度起動し、信頼ダイアログを承認してください")
                return
            with open(CLAUDE_JSON_PATH, "r", encoding="utf-8") as f:
                claude_config = json.load(f)
            projects = claude_config.get("projects", {})
            keys = {resolved_path.replace("/", "\\"), resolved_path.replace("\\", "/")}
            if sys.platform != "win32":
                keys = {resolved_path}
            changed = False
            for key in keys:
                entry = projects.get(key)
                if entry is None:
                    projects[key] = dict(TRUSTED_ENTRY)
                    changed = True
                    print(f"信頼情報を登録: {key}")
                elif not entry.get("hasTrustDialogAccepted"):
                    entry["hasTrustDialogAccepted"] = True
                    changed = True
                    print(f"信頼フラグを有効化: {key}")
            if changed:
                claude_config["projects"] = projects
                with open(CLAUDE_JSON_PATH, "w", encoding="utf-8") as f:
                    json.dump(claude_config, f, indent=2, ensure_ascii=False)
            return
        except PermissionError as e:
            last_error = e
            print(f"  ~/.claude.json がロック中（同時起動？）。再試行します: {e}")
            continue
    raise RuntimeError(f"~/.claude.json への信頼登録に失敗しました（再試行切れ）: {last_error}")


def resolve_claude_cmd():
    """claude CLI の実行ファイルを探す。"""
    return shutil.which("claude") or shutil.which("claude.cmd") or "claude"


def _add_dir_args(add_dirs):
    """`--add-dir <dir>` を並べる。

    🔴 `--add-dir` は可変長（後続の位置引数も取り込む）なので、必ず別のオプションの直前
    （claude の直後）に置く。末尾に置くと初期プロンプトまでディレクトリ名として飲み込まれる。
    """
    args = []
    for d in add_dirs or ():
        args += ["--add-dir", str(d)]
    return args


def build_claude_args(title, named, remote_control, extra_args, add_dirs):
    """claude 本体に渡す引数列（実行ファイル名を除く）を組み立てる。"""
    args = _add_dir_args(add_dirs)
    if remote_control:
        # セッション名をタブ名と同じ文字列で明示する（省略すると cwd 名＋連番になりタブと対応が取れない）
        args += ["--remote-control", title]
    if named:
        # 役割指定ありのときだけ --name も付ける（cross-session messaging の宛先名・/resume の表示名）
        args += ["--name", title]
    return args + list(extra_args)


def build_wt_command(claude_cmd, resolved, title, role, claude_args):
    """Windows Terminal で新しいタブを開くコマンドを組み立てる。"""
    # --suppressApplicationTitle: Claude Code がエスケープシーケンスでタイトルを上書きするのを抑止する
    cmd = ["wt", "--title", title, "--suppressApplicationTitle"]
    if role is not None:
        cmd += ["--tabColor", ROLES[role][1]]
    profile = os.environ.get(WT_PROFILE_ENV)
    if profile:
        cmd += ["-p", profile]
    return cmd + ["-d", resolved, "--", claude_cmd, *claude_args]


def build_bg_command(claude_cmd, title, extra_args, add_dirs):
    """`claude --bg --name <タブ名>` の起動コマンドを組み立てる（opt-in）。

    --bg は -p と併用不可。プロンプトは位置引数。--remote-control とは併用しない。
    """
    return [claude_cmd, *_add_dir_args(add_dirs), "--bg", "--name", title] + list(extra_args)


def _quote_posix(arg):
    return "'" + arg.replace("'", "'\\''") + "'"


def launch_tmux(resolved, title, claude_cmd, claude_args, env):
    """tmux: 現在の tmux セッションに新しいウィンドウを作る。"""
    shell_cmd = " ".join([_quote_posix(claude_cmd)] + [_quote_posix(a) for a in claude_args])
    subprocess.run(["tmux", "new-window", "-n", title, "-c", resolved, shell_cmd], env=env, check=True)


def launch_iterm(resolved, title, claude_cmd, claude_args, env):
    """macOS iTerm2: 新しいタブを開く。"""
    shell_cmd = "cd " + _quote_posix(resolved) + " && " + " ".join(
        [_quote_posix(claude_cmd)] + [_quote_posix(a) for a in claude_args])
    script_text = shell_cmd.replace("\\", "\\\\").replace('"', '\\"')
    osascript = f"""
    tell application "iTerm"
        tell current window
            create tab with default profile
            tell current session
                set name to "{title.replace('"', "'")}"
                write text "{script_text}"
            end tell
        end tell
    end tell
    """
    subprocess.run(["osascript", "-e", osascript], env=env, check=True)


def append_launch_log(resolved, title, role, plan_id, mode):
    """起動記録を JSONL に 1 行追記する。

    費用・生存確認の突き合わせ用の付帯記録であり、起動の前提ではない。
    書けなければ警告を出して起動は続ける（黙って握りつぶさない）。
    """
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "launch",
        "project_path": resolved,
        "tab_name": title,
        "role": role,
        "plan_id": plan_id,
        "mode": mode,
    }
    try:
        LAUNCH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LAUNCH_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"起動記録: {LAUNCH_LOG_PATH}")
    except OSError as e:
        print(f"警告: 起動記録を書けませんでした（{e}）。セッションは起動済みです", file=sys.stderr)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(usage_text())
        return 1

    try:
        opts, extra_args = split_launcher_args(argv[1:])
    except UsageError as e:
        print(f"エラー: {e}")
        print(usage_text())
        return 1

    project_path = Path(argv[0])
    if not project_path.is_dir():
        print(f"エラー: ディレクトリが見つかりません: {project_path}（相対パスは cwd 基準）")
        return 1
    project_path = project_path.resolve()
    resolved = str(project_path)

    role = opts["role"]
    if role is None and opts["task"] is not None:
        role = "single"
    named = role is not None
    title = build_title(project_path, role, opts["task"], opts["plan_id"])
    _, derived_plan = derive_project_and_plan(project_path)
    plan_id = opts["plan_id"] or derived_plan

    # オーケストレーターは全体設定の既定に関わらず default モードで起動する
    # （呼び出し側が権限モードを明示したときはそちらを優先）
    if role == "orchestrator" and not any(
        a == "--permission-mode" or a.startswith("--permission-mode=")
        or a == "--dangerously-skip-permissions"
        for a in extra_args
    ):
        extra_args = ["--permission-mode", "default", *extra_args]

    claude_cmd = resolve_claude_cmd()
    # worktree から起動するときは本流ルートを --add-dir で足す（呼び出し側が渡していれば足さない）
    main_root = worktree_root(project_path)
    add_dirs = [main_root] if main_root is not None and "--add-dir" not in extra_args else []

    if opts["bg"]:
        mode = "bg"
        cmd = build_bg_command(claude_cmd, title, extra_args, add_dirs)
    else:
        claude_args = build_claude_args(title, named, not opts["no_remote_control"], extra_args, add_dirs)
        if sys.platform == "win32":
            mode = "wt"
            cmd = build_wt_command(claude_cmd, resolved, title, role, claude_args)
        elif sys.platform == "darwin":
            mode = "iterm"
            cmd = None
        elif os.environ.get("TMUX"):
            mode = "tmux"
            cmd = None
        else:
            print("エラー: 対応する端末がありません（Windows Terminal / iTerm2 / tmux 内で実行してください）")
            return 1

    print(f"Claude CLI: {claude_cmd}")
    print(f"プロジェクト: {resolved}")
    print(f"タブタイトル: {title}")

    if opts["dry_run"]:
        print("（--dry-run: 起動しません）")
        shown = cmd if cmd is not None else [claude_cmd, *claude_args]
        print(f"方式: {mode}")
        print("コマンド: " + " ".join(json.dumps(c, ensure_ascii=False) if " " in c else c for c in shown))
        return 0

    if mode == "wt" and not shutil.which("wt"):
        print("エラー: Windows Terminal (wt) が見つかりません。Microsoft Store から入れてください")
        return 1

    register_trust(resolved)
    if main_root is not None:
        inherit_mcp_approval(main_root, project_path)

    # CLAUDECODE 環境変数を除外（入れ子セッション検出の回避）
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    if mode == "bg":
        result = subprocess.run(cmd, env=env, cwd=resolved)
        if result.returncode != 0:
            print(f"エラー: claude --bg が終了コード {result.returncode} で失敗しました")
            return result.returncode
        print("バックグラウンドセッションを起動しました（claude agents で一覧・claude attach <id> で接続）")
    elif mode == "wt":
        subprocess.Popen(cmd, env=env)
        print("新しい Claude Code セッションを起動しました")
    elif mode == "iterm":
        launch_iterm(resolved, title, claude_cmd, claude_args, env)
        print("新しい Claude Code セッションを起動しました（iTerm2）")
    else:
        launch_tmux(resolved, title, claude_cmd, claude_args, env)
        print("新しい Claude Code セッションを起動しました（tmux）")

    append_launch_log(resolved, title, role, plan_id, mode)
    if not opts["bg"] and not opts["no_remote_control"]:
        print(f"Remote Control で「{title}」に接続してください")
    return 0


if __name__ == "__main__":
    sys.exit(main())
