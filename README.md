# csess

A cross-agent session picker for Claude, Codex, and Amp.

Shows all sessions in one table. Pick one, get the resume command copied to your clipboard.

## Setup

```zsh
alias csess='python3 /path/to/csess/csess.py'
```

Add that to your `~/.zshrc` and source it.

## Usage

```
csess
csess --search "rate limiting"
csess -s frontend
```

Navigate with arrow keys (or `j`/`k`), press `Enter` to select, `q` to quit.

`--search` (or `-s`) filters sessions before opening the table. Matches against agent, project, and session name.

## Sample output

```
Date          Agent   Project                         Session
2026-04-13    claude  ~/code/my-api                   add rate limiting to the auth e…
2026-04-13    amp     Amp Cloud                       fix the onboarding flow
2026-04-12    codex   ~/work/data-pipeline            rewrite the ETL job to use stre…
2026-04-12    claude  ~/code/frontend                 why is the sidebar flickering o…

  4/177  |  ↑↓ navigate  |  Enter select  |  q quit
```

Selecting a row copies the right resume command for that agent:

```
# claude
cd "/Users/alex/code/my-api" && claude --resume f3a91c2d-7e04-4b6f-85dc-1a2b3c4d5e6f

# codex
codex resume -C "/Users/alex/work/data-pipeline" 02ab4512-fc31-48e7-b901-d2e3f4a5b6c7

# amp
amp threads continue T-02cd6734-a1b2-43e8-9f10-e2f3a4b5c6d7
```

Paste it in your terminal to resume.

## Requirements

Python 3 (ships with macOS). No dependencies.
