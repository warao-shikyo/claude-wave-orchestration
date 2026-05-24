"""Launch a new Claude Code session in its own terminal window.

Designed for Windows + Windows Terminal (`wt`). Adapt the subprocess call
for tmux / iTerm / GNOME Terminal on other platforms — see the bottom of
this file for hooks.

Usage:
    python launch_claude.py <project_path> [starter_prompt]

Examples:
    python launch_claude.py .worktrees/123 "あなたは plan 123 担当です。..."
    python launch_claude.py /home/me/projects/foo

What it does:
    1. Ensures the project path exists
    2. Registers the project as "trusted" in ~/.claude.json (skips if already)
    3. Launches `claude` CLI in a new Windows Terminal tab, cd'd into the project
    4. Passes the starter prompt as a CLI argument so the session starts with it

What it does NOT do:
    - Wait for the session to finish
    - Track session liveness
    - Manage worktree creation (that's the orchestrator's job)
    - Update _progress.md
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

CLAUDE_JSON_PATH = Path.home() / ".claude.json"
LOCK_RETRY_DELAYS = [1, 2, 4, 8]  # exponential backoff for ~/.claude.json lock contention


def usage_and_exit():
    print("Usage: python launch_claude.py <project_path> [starter_prompt] [extra claude args ...]")
    print()
    print("Examples:")
    print("  python launch_claude.py .worktrees/123 'You are plan 123 owner. ...'")
    print("  python launch_claude.py /home/me/projects/foo")
    sys.exit(1)


def register_trust(project_key: str) -> None:
    """Register the project as trusted in ~/.claude.json.

    Retries on PermissionError (file lock from concurrent launchers).
    """
    last_error = None
    for delay in [0] + LOCK_RETRY_DELAYS:
        if delay:
            time.sleep(delay)
        try:
            if not CLAUDE_JSON_PATH.exists():
                # First run — nothing to update yet, Claude CLI will create the file
                return

            with open(CLAUDE_JSON_PATH, "r", encoding="utf-8") as f:
                claude_config = json.load(f)

            projects = claude_config.get("projects", {})
            if project_key in projects:
                # Already trusted, nothing to do
                return

            projects[project_key] = {
                "allowedTools": [],
                "mcpContextUris": [],
                "enabledMcpjsonServers": [],
                "disabledMcpjsonServers": [],
                "hasTrustDialogAccepted": True,
                "projectOnboardingSeenCount": 0,
                "hasClaudeMdExternalIncludesApproved": False,
                "hasClaudeMdExternalIncludesWarningShown": False,
            }
            claude_config["projects"] = projects

            with open(CLAUDE_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(claude_config, f, indent=2, ensure_ascii=False)
            return

        except PermissionError as e:
            last_error = e
            print(f"  ~/.claude.json locked (concurrent launch?), retrying in {delay}s...")
            continue

    # All retries exhausted
    print(f"ERROR: could not register project after retries: {last_error}")
    sys.exit(1)


def resolve_claude_cmd() -> str:
    """Find the claude CLI executable."""
    cmd = shutil.which("claude") or shutil.which("claude.cmd") or "claude"
    return cmd


def launch_in_new_window_windows(project_path: str, tab_title: str, claude_cmd: str, extra_args: list) -> None:
    """Windows: open in a new Windows Terminal tab."""
    # Exclude CLAUDECODE env to avoid nested-session detection
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    cmd = ["wt", "--title", tab_title, "-d", project_path, "--", claude_cmd] + extra_args
    subprocess.Popen(cmd, env=env)


def launch_in_new_window_tmux(project_path: str, tab_title: str, claude_cmd: str, extra_args: list) -> None:
    """tmux: create a new window with claude in it."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    # Assumes you're inside a tmux session already
    args_str = " ".join(f"'{a}'" for a in extra_args)
    subprocess.run([
        "tmux", "new-window",
        "-n", tab_title,
        "-c", project_path,
        f"{claude_cmd} {args_str}",
    ], env=env)


def launch_in_new_window_iterm(project_path: str, tab_title: str, claude_cmd: str, extra_args: list) -> None:
    """macOS iTerm2: open a new tab."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    args_str = " ".join(f"'{a}'" for a in extra_args)
    osascript = f"""
    tell application "iTerm"
        tell current window
            create tab with default profile
            tell current session
                write text "cd '{project_path}' && {claude_cmd} {args_str}"
            end tell
        end tell
    end tell
    """
    subprocess.run(["osascript", "-e", osascript], env=env)


def launch_session(project_path: str, extra_args: list) -> None:
    """Pick the right launcher for the platform."""
    tab_title = Path(project_path).name or "claude"
    claude_cmd = resolve_claude_cmd()

    print(f"Claude CLI: {claude_cmd}")
    print(f"Project: {project_path}")
    print(f"Tab title: {tab_title}")

    if sys.platform == "win32":
        # Windows Terminal
        if not shutil.which("wt"):
            print("ERROR: Windows Terminal (wt) not found. Install from Microsoft Store.")
            sys.exit(1)
        launch_in_new_window_windows(project_path, tab_title, claude_cmd, extra_args)
    elif sys.platform == "darwin":
        # macOS — assume iTerm2 (adapt to Terminal.app if you prefer)
        if not shutil.which("osascript"):
            print("ERROR: osascript not found.")
            sys.exit(1)
        launch_in_new_window_iterm(project_path, tab_title, claude_cmd, extra_args)
    elif os.environ.get("TMUX"):
        # Inside tmux
        launch_in_new_window_tmux(project_path, tab_title, claude_cmd, extra_args)
    else:
        print("ERROR: No supported terminal multiplexer found.")
        print("Run inside tmux, or on Windows/macOS.")
        sys.exit(1)

    print("New Claude Code session launched.")


def main():
    if len(sys.argv) < 2:
        usage_and_exit()

    project_path = Path(sys.argv[1])
    extra_args = sys.argv[2:]  # starter prompt + any further CLI args

    if not project_path.is_dir():
        print(f"ERROR: directory not found: {project_path}")
        sys.exit(1)

    resolved = str(project_path.resolve())
    project_key = resolved.replace("/", "\\") if sys.platform == "win32" else resolved

    print(f"Resolved path: {resolved}")
    print(f"Project key (~/.claude.json): {project_key}")

    register_trust(project_key)
    launch_session(resolved, extra_args)


if __name__ == "__main__":
    main()
