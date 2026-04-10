# csess

Browse your Claude Code session history and copy a resume command to your clipboard.

Reads `~/.claude/history.jsonl`, shows all sessions in a table, and when you pick one it copies `cd "/path/to/project" && claude --resume <id>` to the clipboard.

## Setup

```zsh
alias csess='python3 /path/to/csess/csess.py'
```

Add that to your `~/.zshrc` and source it.

## Usage

```
csess
```

Navigate with arrow keys (or `j`/`k`), press `Enter` to select, `q` to quit.

## Sample output

```
Date          Project                              Session
2026-04-10    ~/code/my-api                        add rate limiting to the auth e…
2026-04-09    ~/code/frontend                      why is the sidebar flickering o…
2026-04-08    ~/work/data-pipeline                 rewrite the ETL job to use stre…

  3/42  |  ↑↓ navigate  |  Enter select  |  q quit
```

Selecting the second row copies this to clipboard:

```
cd "/Users/alex/code/frontend" && claude --resume b2e7f1a3-9c4d-4e8b-a12f-3d6c8e0f4b91
```

Paste it in your terminal to resume.

## Requirements

Python 3 (ships with macOS). No dependencies.
