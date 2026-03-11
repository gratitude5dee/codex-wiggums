# Benchmarking

Ralph ships with two benchmark paths.

## Local Smoke

Run:

```bash
python ~/.codex/skills/ralph-wiggum/scripts/ralph_bench.py smoke
```

This validates:

- template rendering includes the promise contract
- queue lifecycle emits wrapped prompts
- status reporting stays machine-readable

Reports are written to the Ralph benchmark state directory outside the skill folder.

## Harbor / SkillsBench

If Harbor is installed, Ralph can forward to a Harbor dataset:

```bash
python ~/.codex/skills/ralph-wiggum/scripts/ralph_bench.py harbor \
  --dataset /path/to/skillsbench/dataset \
  --agent codex
```

Recommended comparison workflow:

1. Run the same dataset without Ralph-specific prompting.
2. Run again with Ralph templates and completion contracts.
3. Compare pass rate, iteration count, and failure shape.
