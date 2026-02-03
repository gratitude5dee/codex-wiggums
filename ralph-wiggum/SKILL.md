---
name: ralph-wiggum
description: Prompt loop and queue control for Codex, mirroring Ralph Wiggum loop semantics. Use when you need to repeat a prompt, queue iterations, resume with /ralph-next, check /ralph-status, or cancel with /cancel-ralph.
---

# Ralph Wiggum

## Overview

Provide a manual prompt loop and queue so Codex can repeat the same request for multiple iterations and move through queued prompts safely.

## Install

- **Fast install**: Use `$skill-installer` and point it at `https://github.com/gratitude5dee/codex-wiggums`.
- **Manual install**: Place `ralph-wiggum` under `~/.codex/skills/ralph-wiggum`.

Restart Codex after installation.

## Quick Start

```
python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py loop --prompt "<text>" --max-iterations 5
python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py next
python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py status
```

## Command Map

- `/ralph-loop [N]` -> `ralph_queue.py loop --prompt "<last user prompt>" --max-iterations N`
- `/ralph-next` -> `ralph_queue.py next`
- `/ralph-status` -> `ralph_queue.py status`
- `/cancel-ralph` -> `ralph_queue.py cancel`

## Prompt Selection

- Use the most recent non-command user request as the prompt.
- If the user supplies an explicit prompt, use that instead.
- If the last request is ambiguous or multi-part, confirm the exact prompt before looping.

## Queue Semantics

- `loop` creates a loop item with `remaining = max_iterations`.
- If no active item exists, the new item becomes active; otherwise it is appended to the queue.
- `next` returns the active prompt and decrements `remaining` by 1.
- When `remaining` reaches 0, clear the active item and promote the next queued item, if any.

## Safety Guardrails

- Default `max-iterations` is 5.
- Hard cap is 25 unless `--force` is explicitly supplied.
- If the user requests more than 10 iterations, confirm before starting the loop.
- Always honor `/cancel-ralph` immediately.

## Script Usage

Start a loop:
`python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py loop --prompt "<text>" --max-iterations 5`

Read prompt from a file:
`python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py loop --prompt-file ./prompt.txt`

Read prompt from stdin:
`cat prompt.txt | python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py loop --prompt-stdin`

Get the next prompt:
`python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py next`

Check status:
`python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py status`

Cancel and clear:
`python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py cancel`

Use `--json` with `loop`, `next`, or `status` for machine-readable output.

## JSON Output Examples

`status --json`:
```
{
  "active": true,
  "active_id": "...",
  "active_remaining": 2,
  "active_max_iterations": 5,
  "active_created_at": "2026-02-03T18:00:00+00:00",
  "queue_size": 1
}
```

`next --json`:
```
{
  "prompt": "...",
  "remaining": 1,
  "max_iterations": 5,
  "id": "...",
  "created_at": "2026-02-03T18:00:00+00:00",
  "queue_size": 0,
  "finished": false
}
```

## State File

The queue state is stored at:
`~/.codex/skills/ralph-wiggum/state/queue.json`

Shape:
```
{
  "version": 1,
  "active": {
    "id": "...",
    "prompt": "...",
    "remaining": 3,
    "max_iterations": 5,
    "created_at": "2026-02-03T18:00:00+00:00"
  },
  "queue": [
    {
      "id": "...",
      "prompt": "...",
      "remaining": 5,
      "max_iterations": 5,
      "created_at": "2026-02-03T18:02:00+00:00"
    }
  ]
}
```
