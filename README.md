# Codex Wiggums

Manual prompt loop and queue for Codex, inspired by the Ralph Wiggum loop pattern.

## What This Does

- Loop a prompt for N iterations.
- Queue additional prompts behind the active loop.
- Resume with `/ralph-next` and inspect `/ralph-status`.
- Cancel immediately with `/cancel-ralph`.

## Install

1. Clone this repo.
2. Place the `ralph-wiggum` folder under `~/.codex/skills`.
3. Restart the Codex app if the skill does not appear.

## Quick Start

```bash
python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py loop --prompt "<text>" --max-iterations 5
python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py next
python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py status
```

## Command Map

- `/ralph-loop [N]` -> `ralph_queue.py loop --prompt "<last user prompt>" --max-iterations N`
- `/ralph-next` -> `ralph_queue.py next`
- `/ralph-status` -> `ralph_queue.py status`
- `/cancel-ralph` -> `ralph_queue.py cancel`

## CLI Notes

- Default `max-iterations` is 5.
- Hard cap is 25 unless `--force` is supplied.
- Use `--json` with `loop`, `next`, or `status` for machine-readable output.
- State is stored at `~/.codex/skills/ralph-wiggum/state/queue.json`.

## License

MIT
