#!/usr/bin/env python3
import curses
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

HISTORY_FILE = os.path.expanduser("~/.claude/history.jsonl")
DATE_W = 12
PROJECT_W = 35


def trunc(s, width):
    if len(s) <= width:
        return s.ljust(width)
    return s[: width - 1] + "…"


def load_sessions():
    sessions = {}
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
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
        if ts_ms:
            dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).astimezone()
            date_str = dt.strftime("%Y-%m-%d")
        else:
            date_str = "unknown"
        project = data["project"]
        home = os.path.expanduser("~")
        if project.startswith(home):
            project = "~" + project[len(home):]
        result.append((ts_ms, date_str, project, data["display"], sid))
    result.sort(key=lambda x: x[0], reverse=True)
    return result


def main(stdscr):
    sessions = load_sessions()
    if not sessions:
        stdscr.addstr(0, 0, "No sessions found in ~/.claude/history.jsonl")
        stdscr.refresh()
        stdscr.getch()
        return None

    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)   # selected row
    curses.init_pair(2, curses.COLOR_CYAN, -1)                   # header

    cursor = 0
    offset = 0

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        display_w = max(w - DATE_W - PROJECT_W - 4, 10)
        visible = h - 2  # header + status line

        header = (
            trunc("Date", DATE_W)
            + "  "
            + trunc("Project", PROJECT_W)
            + "  "
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
            _, date_str, project, display, _ = sessions[idx]
            row = (
                trunc(date_str, DATE_W)
                + "  "
                + trunc(project, PROJECT_W)
                + "  "
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

        status = f"  {cursor + 1}/{len(sessions)}  |  ↑↓ navigate  |  Enter select  |  q quit"
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
            _, _, project, _, sid = sessions[cursor]
            return sid, project
        elif key in (ord("q"), 27):  # q or Esc
            return None


def run():
    result = curses.wrapper(main)
    if result:
        sid, project = result
        # Expand ~ back to full path for cd
        project_full = os.path.expanduser(project)
        cmd = f'cd "{project_full}" && claude --resume {sid}'
        subprocess.run(["pbcopy"], input=cmd.encode(), check=True)
        print(f"Copied to clipboard: {cmd}")
    else:
        print("No session selected.")


if __name__ == "__main__":
    run()
