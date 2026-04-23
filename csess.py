#!/usr/bin/env python3
import argparse
import curses
import json
import os
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

CLAUDE_HISTORY = os.path.expanduser("~/.claude/history.jsonl")
CODEX_HISTORY = os.path.expanduser("~/.codex/history.jsonl")
CODEX_SESSIONS_DIR = os.path.expanduser("~/.codex/sessions")

DATE_W = 12
AGENT_W = 6
PROJECT_W = 30


def trunc(s, width):
    if len(s) <= width:
        return s.ljust(width)
    return s[: width - 1] + "…"


def shorten_home(path):
    home = os.path.expanduser("~")
    if path.startswith(home):
        return "~" + path[len(home):]
    return path


def load_claude():
    if not os.path.exists(CLAUDE_HISTORY):
        return []
    sessions = {}
    with open(CLAUDE_HISTORY, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            sid = entry.get("sessionId", "")
            if not sid:
                continue
            ts = entry.get("timestamp", 0) or 0
            project = entry.get("project", "") or ""
            display = entry.get("display", "") or ""
            if sid not in sessions:
                sessions[sid] = {"ts": ts, "project": project, "display": display}
            else:
                if ts > sessions[sid]["ts"]:
                    sessions[sid]["ts"] = ts
                    sessions[sid]["project"] = project
                if not sessions[sid]["display"] and display:
                    sessions[sid]["display"] = display
    result = []
    for sid, data in sessions.items():
        ts_ms = data["ts"]
        date_str = (
            datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).astimezone().strftime("%Y-%m-%d")
            if ts_ms else "unknown"
        )
        result.append((ts_ms, date_str, "claude", shorten_home(data["project"]), data["display"], sid))
    return result


def build_codex_cwd_index():
    """Read the first line of each codex session file to build {session_id: cwd}."""
    index = {}
    base = Path(CODEX_SESSIONS_DIR)
    if not base.exists():
        return index
    for f in base.rglob("*.jsonl"):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                first = fh.readline().strip()
                if not first:
                    continue
                entry = json.loads(first)
                if entry.get("type") == "session_meta":
                    payload = entry.get("payload", {})
                    sid = payload.get("id", "")
                    cwd = payload.get("cwd", "")
                    if sid and cwd:
                        index[sid] = cwd
        except Exception:
            continue
    return index


def load_codex():
    if not os.path.exists(CODEX_HISTORY):
        return []
    cwd_index = build_codex_cwd_index()
    sessions = {}
    with open(CODEX_HISTORY, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            sid = entry.get("session_id", "")
            if not sid:
                continue
            ts = (entry.get("ts", 0) or 0) * 1000  # seconds -> ms
            display = entry.get("text", "") or ""
            if sid not in sessions:
                sessions[sid] = {"ts": ts, "display": display}
            else:
                if ts > sessions[sid]["ts"]:
                    sessions[sid]["ts"] = ts
                if not sessions[sid]["display"] and display:
                    sessions[sid]["display"] = display
    result = []
    for sid, data in sessions.items():
        ts_ms = data["ts"]
        date_str = (
            datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).astimezone().strftime("%Y-%m-%d")
            if ts_ms else "unknown"
        )
        cwd = cwd_index.get(sid, "")
        project = shorten_home(cwd) if cwd else "unknown"
        result.append((ts_ms, date_str, "codex", project, data["display"], sid))
    return result


def parse_relative_time(s):
    now = datetime.now(tz=timezone.utc)
    s = s.strip().lower()
    try:
        if s.endswith("m ago"):
            delta = timedelta(minutes=int(s[:-5].strip()))
        elif s.endswith("h ago"):
            delta = timedelta(hours=int(s[:-5].strip()))
        elif s.endswith("d ago"):
            delta = timedelta(days=int(s[:-5].strip()))
        elif s.endswith("w ago"):
            delta = timedelta(weeks=int(s[:-5].strip()))
        else:
            return 0
        return int((now - delta).timestamp() * 1000)
    except (ValueError, AttributeError):
        return 0


def load_amp():
    try:
        proc = subprocess.run(
            ["amp", "threads", "list"],
            capture_output=True, text=True, timeout=10
        )
        if proc.returncode != 0:
            return []
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    result = []
    for line in proc.stdout.strip().splitlines()[2:]:  # skip header + separator
        line = line.rstrip()
        if not line:
            continue
        # columns (right to left): thread_id, messages, visibility, "ago", time_value, title
        parts = line.rsplit(None, 5)
        if len(parts) != 6 or not parts[5].startswith("T-"):
            continue
        title = parts[0].strip()
        last_updated = parts[1] + " " + parts[2]  # e.g. "3m ago"
        thread_id = parts[5]
        ts_ms = parse_relative_time(last_updated)
        date_str = (
            datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).astimezone().strftime("%Y-%m-%d")
            if ts_ms else "unknown"
        )
        result.append((ts_ms, date_str, "amp", "Amp Cloud", title, thread_id))
    return result


def load_all():
    sessions = load_claude() + load_codex() + load_amp()
    sessions.sort(key=lambda x: x[0], reverse=True)
    return sessions


def main(stdscr, search=None):
    sessions = load_all()
    if search:
        q = search.lower()
        sessions = [s for s in sessions if any(q in f.lower() for f in (s[1], s[2], s[3], s[4]))]
    if not sessions:
        stdscr.addstr(0, 0, "No sessions found.")
        stdscr.refresh()
        stdscr.getch()
        return None

    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_CYAN, -1)

    cursor = 0
    offset = 0

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        display_w = max(w - DATE_W - AGENT_W - PROJECT_W - 6, 10)
        visible = h - 2

        header = (
            trunc("Date", DATE_W) + "  "
            + trunc("Agent", AGENT_W) + "  "
            + trunc("Project", PROJECT_W) + "  "
            + trunc("Session", display_w)
        )
        try:
            stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
            stdscr.addstr(0, 0, header[:w - 1])
            stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
        except curses.error:
            pass

        if cursor < offset:
            offset = cursor
        if cursor >= offset + visible:
            offset = cursor - visible + 1

        for i, idx in enumerate(range(offset, min(offset + visible, len(sessions)))):
            _, date_str, agent, project, display, _ = sessions[idx]
            row = (
                trunc(date_str, DATE_W) + "  "
                + trunc(agent, AGENT_W) + "  "
                + trunc(project, PROJECT_W) + "  "
                + trunc(display, display_w)
            )[:w - 1]
            y = i + 1
            try:
                if idx == cursor:
                    stdscr.attron(curses.color_pair(1))
                    stdscr.insstr(y, 0, row.ljust(w - 1))
                    stdscr.attroff(curses.color_pair(1))
                else:
                    stdscr.insstr(y, 0, row)
            except curses.error:
                pass

        filter_hint = f"  filter: {search}  |" if search else ""
        status = f"{filter_hint}  {cursor + 1}/{len(sessions)}  |  ↑↓ navigate  |  Enter select  |  q quit"
        try:
            stdscr.addstr(h - 1, 0, status[:w - 1])
        except curses.error:
            pass
        stdscr.refresh()

        key = stdscr.getch()
        if key in (curses.KEY_UP, ord("k")):
            cursor = max(0, cursor - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = min(len(sessions) - 1, cursor + 1)
        elif key in (ord("\n"), ord("\r"), curses.KEY_ENTER):
            _, _, agent, project, _, sid = sessions[cursor]
            return agent, sid, project
        elif key in (ord("q"), 27):
            return None


def run():
    parser = argparse.ArgumentParser(description="Cross-agent session picker")
    parser.add_argument("--search", "-s", metavar="TERM", help="Filter sessions by search term")
    args = parser.parse_args()
    result = curses.wrapper(main, search=args.search)
    if not result:
        print("No session selected.")
        return
    agent, sid, project = result
    if agent == "claude":
        project_full = os.path.expanduser(project)
        cmd = f'cd "{project_full}" && claude --resume {sid}'
    elif agent == "codex":
        if project and project != "unknown":
            project_full = os.path.expanduser(project)
            cmd = f'codex resume -C "{project_full}" {sid}'
        else:
            cmd = f'codex resume {sid}'
    elif agent == "amp":
        cmd = f'amp threads continue {sid}'
    else:
        cmd = sid
    subprocess.run(["pbcopy"], input=cmd.encode(), check=True)
    print(f"Copied to clipboard: {cmd}")


if __name__ == "__main__":
    run()
