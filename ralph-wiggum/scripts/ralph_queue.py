#!/usr/bin/env python3
import argparse
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MAX_ITERATIONS = 5
HARD_MAX_ITERATIONS = 25
STATE_VERSION = 1


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def state_path() -> Path:
    return skill_root() / "state" / "queue.json"


def default_state() -> dict:
    return {"version": STATE_VERSION, "active": None, "queue": []}


def normalize_state(state: object) -> dict:
    if not isinstance(state, dict):
        return default_state()
    active = state.get("active")
    queue = state.get("queue")
    if active is not None and not isinstance(active, dict):
        active = None
    if not isinstance(queue, list):
        queue = []
    return {
        "version": state.get("version", STATE_VERSION),
        "active": active,
        "queue": queue,
    }


def load_state() -> dict:
    path = state_path()
    if not path.exists():
        return default_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default_state()
    return normalize_state(data)


def write_state(state: dict) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        delete=False,
        dir=path.parent,
        encoding="utf-8",
    ) as tmp:
        json.dump(state, tmp, indent=2)
        tmp.write("\n")
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_item(prompt: str, max_iterations: int) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "prompt": prompt,
        "remaining": max_iterations,
        "max_iterations": max_iterations,
        "created_at": iso_now(),
    }


def safe_int(value: object, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def clamp_iterations(value: int, force: bool) -> int:
    if value <= 0:
        raise ValueError("max-iterations must be >= 1")
    if value > HARD_MAX_ITERATIONS and not force:
        raise ValueError(
            f"max-iterations exceeds hard cap ({HARD_MAX_ITERATIONS}); use --force to override"
        )
    return value


def promote_if_needed(state: dict) -> None:
    if state.get("active") is None and state.get("queue"):
        state["active"] = state["queue"].pop(0)


def read_prompt(args: argparse.Namespace) -> str:
    sources = [bool(args.prompt), bool(args.prompt_file), bool(args.prompt_stdin)]
    if sum(sources) > 1:
        raise ValueError("use only one of --prompt, --prompt-file, or --prompt-stdin")

    if args.prompt:
        return str(args.prompt).strip()

    if args.prompt_file:
        path = Path(args.prompt_file)
        try:
            return path.read_text(encoding="utf-8").strip()
        except Exception as exc:
            raise ValueError(f"failed to read prompt file: {exc}")

    if args.prompt_stdin:
        return sys.stdin.read().strip()

    return ""


def cmd_loop(args: argparse.Namespace) -> int:
    try:
        prompt = read_prompt(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not prompt:
        print("error: prompt is required", file=sys.stderr)
        return 2

    max_iterations = args.max_iterations
    if max_iterations is None:
        max_iterations = DEFAULT_MAX_ITERATIONS

    try:
        max_iterations = clamp_iterations(max_iterations, args.force)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    state = load_state()
    item = new_item(prompt, max_iterations)
    queued = state.get("active") is not None
    if queued:
        state["queue"].append(item)
    else:
        state["active"] = item

    write_state(state)

    if args.json:
        output = {
            "queued": queued,
            "id": item["id"],
            "prompt": item["prompt"],
            "remaining": item["remaining"],
            "max_iterations": item["max_iterations"],
            "created_at": item["created_at"],
            "queue_size": len(state.get("queue", [])),
        }
        print(json.dumps(output, indent=2))
        return 0

    if queued:
        print("Queued loop item.")
    else:
        print("Started loop item.")
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    state = load_state()
    promote_if_needed(state)

    active = state.get("active")
    if not active:
        print("queue empty", file=sys.stderr)
        return 1

    prompt = str(active.get("prompt", ""))
    remaining = safe_int(active.get("remaining"), 0)
    max_iterations = safe_int(active.get("max_iterations"), remaining)
    created_at = active.get("created_at")

    if remaining <= 0:
        state["active"] = None
        promote_if_needed(state)
        write_state(state)
        print("queue empty", file=sys.stderr)
        return 1

    remaining -= 1
    active["remaining"] = remaining

    finished = remaining <= 0
    if finished:
        state["active"] = None
        promote_if_needed(state)

    write_state(state)

    if args.json:
        output = {
            "prompt": prompt,
            "remaining": remaining,
            "max_iterations": max_iterations,
            "id": active.get("id"),
            "created_at": created_at,
            "queue_size": len(state.get("queue", [])),
            "finished": finished,
        }
        print(json.dumps(output, indent=2))
        return 0

    print(prompt)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state = load_state()
    active = state.get("active")
    queue = state.get("queue") or []

    if active:
        remaining = safe_int(active.get("remaining"), 0)
        max_iterations = safe_int(active.get("max_iterations"), 0)
        active_id = active.get("id")
        active_created_at = active.get("created_at")
    else:
        remaining = 0
        max_iterations = 0
        active_id = None
        active_created_at = None

    output = {
        "active": bool(active),
        "active_id": active_id,
        "active_remaining": remaining,
        "active_max_iterations": max_iterations,
        "active_created_at": active_created_at,
        "queue_size": len(queue),
    }

    if args.json:
        print(json.dumps(output, indent=2))
        return 0

    if output["active"]:
        print(f"active remaining: {remaining}/{max_iterations}")
    else:
        print("active remaining: 0/0")
    print(f"queued items: {len(queue)}")
    return 0


def cmd_cancel(_: argparse.Namespace) -> int:
    write_state(default_state())
    print("Cleared queue.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local prompt queue for Ralph Wiggum style loops",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    loop_parser = subparsers.add_parser("loop", help="Start or enqueue a loop")
    loop_parser.add_argument("--prompt", help="Prompt text")
    loop_parser.add_argument("--prompt-file", help="Read prompt from a file")
    loop_parser.add_argument(
        "--prompt-stdin",
        action="store_true",
        help="Read prompt from stdin",
    )
    loop_parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help=f"Number of repeats (default {DEFAULT_MAX_ITERATIONS})",
    )
    loop_parser.add_argument(
        "--force",
        action="store_true",
        help=f"Allow max-iterations above {HARD_MAX_ITERATIONS}",
    )
    loop_parser.add_argument("--json", action="store_true", help="JSON output")
    loop_parser.set_defaults(func=cmd_loop)

    next_parser = subparsers.add_parser("next", help="Pop the next prompt")
    next_parser.add_argument("--json", action="store_true", help="JSON output")
    next_parser.set_defaults(func=cmd_next)

    status_parser = subparsers.add_parser("status", help="Show queue status")
    status_parser.add_argument("--json", action="store_true", help="JSON output")
    status_parser.set_defaults(func=cmd_status)

    cancel_parser = subparsers.add_parser("cancel", help="Clear active and queued items")
    cancel_parser.set_defaults(func=cmd_cancel)

    clear_parser = subparsers.add_parser("clear", help="Alias for cancel")
    clear_parser.set_defaults(func=cmd_cancel)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
