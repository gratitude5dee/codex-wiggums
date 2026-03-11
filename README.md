# Codex Wiggums

Ralph Wiggum for Codex: a persistent, verifiable coding loop with prompt templates, sessioned state, and optional benchmark tooling.

## What Changed

- Verifiable loop prompts with explicit `objective`, `done_when`, and `<promise>COMPLETE</promise>` contracts.
- Sessioned queue management with `peek`, `list`, template rendering, and archived history.
- Prompt templates for build, repair, review, and research loops.
- Optional local smoke benchmarks plus Harbor / SkillsBench pass-through.

## Fast Install

From inside Codex:

```text
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

## Quick Start

```bash
python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py loop \
  --template build \
  --prompt "Add user auth to the API" \
  --objective "Ship tested auth support" \
  --done-when "The targeted tests pass and docs are updated"

python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py next
python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py status
```

## Template Commands

```bash
python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py template list
python ~/.codex/skills/ralph-wiggum/scripts/ralph_queue.py template render review --prompt "Review this PR for regressions"
```

## Benchmark Commands

Local smoke regression:

```bash
python ~/.codex/skills/ralph-wiggum/scripts/ralph_bench.py smoke
```

Optional Harbor / SkillsBench run:

```bash
python ~/.codex/skills/ralph-wiggum/scripts/ralph_bench.py harbor --dataset /path/to/dataset --agent codex
```

## Notes

- The installed skill stays standard-library only.
- Runtime state now lives outside the skill folder so installs stay clean.
- The skill path stays top-level for simple GitHub URL installation with `$skill-installer`.
