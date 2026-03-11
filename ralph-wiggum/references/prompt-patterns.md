# Prompt Patterns

Use the smallest pattern that matches the task.

## Build

Use `build` when the request changes behavior, adds code, or needs tests.

- State the user-facing outcome in `--objective`.
- Put the verification rule in `--done-when`.
- Favor red -> green -> cleanup.

## Repair

Use `repair` when the problem is a failure, regression, or flaky workflow.

- Name the failing test, command, or symptom.
- Ask for root cause before broad rewrites.
- Require the fix and the verification to both appear in the response.

## Review

Use `review` when the loop should inspect rather than mutate.

- Focus on bugs, regressions, risky assumptions, and missing tests.
- Require evidence from files, commands, or test output.
- Keep summaries short and findings first.

## Research

Use `research` when Ralph needs to gather evidence before changing code.

- Capture the question, current state, and what evidence will settle it.
- Require source-backed conclusions.
- Convert the output into an implementation brief before queueing a build loop.
