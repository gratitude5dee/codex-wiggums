---
name: ralph-wiggum
description: Persistent prompt loop, template pack, and optional benchmark tooling for Codex. Use when you need to repeat or stage a coding task, wrap it in a verifiable completion contract, render build or review loop templates, or handle /ralph-loop, /ralph-next, /ralph-status, or /cancel-ralph commands.
---

# Ralph Wiggum

## Overview

Provide a persistent coding loop for Codex with reusable prompt templates, explicit done conditions, and a completion promise token.

## Install

- Fast install: Use `$skill-installer` with `https://github.com/gratitude5dee/codex-wiggums`.
- Manual install: Place `ralph-wiggum` under `~/.codex/skills/ralph-wiggum`.

Restart Codex after installation.

## Quick Start

```bash
python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py loop \
  --template build \
  --prompt "Add JWT auth to the API" \
  --objective "Ship tested auth support" \
  --done-when "Targeted tests pass and docs are updated"

python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py next
python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py status
```

## Command Map

- `/ralph-loop [N]`: Queue the last user task with a template, done condition, and completion promise.
- `/ralph-next`: Emit the wrapped prompt for the current Ralph session and decrement one iteration.
- `/ralph-status`: Show the live session, queue depth, archive count, and runtime state directory.
- `/cancel-ralph`: Cancel the live Ralph session or a specific session id.
- `/ralph-template <name>`: Render a reusable build, repair, review, or research template before queueing it.

## Workflow

1. Capture one concrete prompt source.
2. Choose the narrowest template that matches the task.
3. State `--objective` and `--done-when` in verifiable language.
4. Use the emitted wrapped prompt until the task can honestly end with `<promise>COMPLETE</promise>`.

## References

- Read `references/operating-rules.md` for the core loop discipline and promise rules.
- Read `references/prompt-patterns.md` for curated build, repair, review, and research patterns.
- Read `references/benchmarking.md` when you want to compare Ralph changes locally or with Harbor / SkillsBench.

## Script Usage

Start or enqueue a session:
`python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py loop --template build --prompt "<text>" --objective "<outcome>" --done-when "<check>"`

Preview without decrementing:
`python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py peek`

List live and archived sessions:
`python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py list`

Render a template without queueing:
`python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py template render review --prompt "<text>"`

Run local smoke benchmarks:
`python ~/.codex/skills/ralph-wiggum/scripts/ralph_bench.py smoke`

Use `--json` with `loop`, `next`, `peek`, `status`, `list`, `cancel`, and `template` commands for machine-readable output.

## State

Ralph stores runtime state outside the skill folder.

- macOS default: `~/Library/Application Support/ralph-wiggum/queue.json`
- Linux default: `$XDG_STATE_HOME/ralph-wiggum/queue.json` or `~/.local/state/ralph-wiggum/queue.json`

Legacy state from `~/.codex/skills/ralph-wiggum/state/queue.json` is read automatically if it exists.
