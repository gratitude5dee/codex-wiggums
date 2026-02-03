# Codex Wiggums

Manual prompt loop and queue for Codex, inspired by the Ralph Wiggum loop pattern.

## Standards Alignment

This repo follows the Codex skills standard:

- A skill is a folder that contains a required `SKILL.md` with YAML frontmatter (`name` and `description`).
- Optional folders include `scripts/`, `references/`, and `assets/`.
- Skills are discoverable when placed under supported locations like `~/.codex/skills` (user) or `.codex/skills` (repo).

## Fast Install (Recommended)

From within Codex, use the built-in installer and point it at this repo URL:

```
$skill-installer
Install the ralph-wiggum skill from https://github.com/gratitude5dee/codex-wiggums
```

Restart Codex after installation.

## Manual Install

```bash
git clone https://github.com/gratitude5dee/codex-wiggums.git
mkdir -p ~/.codex/skills
cp -R codex-wiggums/ralph-wiggum ~/.codex/skills/ralph-wiggum
```

Alternatively, check the skill into a repo-scoped location:

```bash
mkdir -p .codex/skills
cp -R codex-wiggums/ralph-wiggum .codex/skills/ralph-wiggum
```

Restart Codex after installation.

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
