#!/usr/bin/env python3
import argparse
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from string import Template

DEFAULT_MAX_ITERATIONS = 5
HARD_MAX_ITERATIONS = 25
STATE_VERSION = 2
DEFAULT_TEMPLATE = "build"
DEFAULT_PROMISE = "COMPLETE"
DEFAULT_DONE_WHEN = "The requested work is complete and explicitly verified."
DEFAULT_NOTE = "No extra notes."
ARCHIVE_LIMIT = 100
TEXT_ENCODING = "utf-8"


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def legacy_state_path() -> Path:
    return skill_root() / "state" / "queue.json"


def state_dir() -> Path:
    xdg_state_home = os.environ.get("XDG_STATE_HOME")
    if xdg_state_home:
        return Path(xdg_state_home) / "ralph-wiggum"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ralph-wiggum"
    return Path.home() / ".local" / "state" / "ralph-wiggum"


def state_path() -> Path:
    return state_dir() / "queue.json"


def template_dir() -> Path:
    return skill_root() / "assets" / "templates"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def default_state() -> dict:
    return {"version": STATE_VERSION, "active": None, "queue": [], "archive": []}


def safe_int(value: object, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def unique_strings(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def normalize_item(item: object) -> dict | None:
    if not isinstance(item, dict):
        return None
    prompt = str(item.get("prompt", "")).strip()
    if not prompt:
        return None
    created_at = str(item.get("created_at") or iso_now())
    updated_at = str(item.get("updated_at") or created_at)
    item_id = str(item.get("id") or uuid.uuid4())
    remaining = safe_int(item.get("remaining"), DEFAULT_MAX_ITERATIONS)
    max_iterations = safe_int(item.get("max_iterations"), remaining or DEFAULT_MAX_ITERATIONS)
    if max_iterations < 1:
        max_iterations = DEFAULT_MAX_ITERATIONS
    if remaining < 0:
        remaining = 0
    emitted_count = safe_int(item.get("emitted_count"), max_iterations - remaining)
    if emitted_count < 0:
        emitted_count = 0
    template_name = sanitize_template_name(item.get("template") or DEFAULT_TEMPLATE)
    objective = str(item.get("objective") or prompt).strip()
    done_when = str(item.get("done_when") or DEFAULT_DONE_WHEN).strip()
    note = str(item.get("note") or DEFAULT_NOTE).strip()
    completion_promise = str(item.get("completion_promise") or DEFAULT_PROMISE).strip()
    if not completion_promise:
        completion_promise = DEFAULT_PROMISE
    tags = item.get("tags")
    if not isinstance(tags, list):
        tags = []
    tags = unique_strings([str(tag) for tag in tags])
    session_id = str(item.get("session_id") or item_id)
    return {
        "id": item_id,
        "session_id": session_id,
        "prompt": prompt,
        "objective": objective,
        "done_when": done_when,
        "template": template_name,
        "completion_promise": completion_promise,
        "note": note,
        "tags": tags,
        "remaining": remaining,
        "max_iterations": max_iterations,
        "emitted_count": emitted_count,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def normalize_state(state: object) -> dict:
    if not isinstance(state, dict):
        return default_state()
    active = normalize_item(state.get("active"))
    queue_values = state.get("queue")
    archive_values = state.get("archive")
    if not isinstance(queue_values, list):
        queue_values = []
    if not isinstance(archive_values, list):
        archive_values = []
    queue = [item for item in (normalize_item(value) for value in queue_values) if item]
    archive = [item for item in (normalize_item(value) for value in archive_values) if item]
    return {
        "version": STATE_VERSION,
        "active": active,
        "queue": queue,
        "archive": archive[-ARCHIVE_LIMIT:],
    }


def load_state() -> dict:
    for path in (state_path(), legacy_state_path()):
        if not path.exists():
            continue
        try:
            return normalize_state(json.loads(path.read_text(encoding=TEXT_ENCODING)))
        except Exception:
            return default_state()
    return default_state()


def write_state(state: dict) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_state(state)
    with tempfile.NamedTemporaryFile(
        "w",
        delete=False,
        dir=path.parent,
        encoding=TEXT_ENCODING,
    ) as handle:
        json.dump(normalized, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def sanitize_template_name(raw_value: object) -> str:
    name = str(raw_value or DEFAULT_TEMPLATE).strip()
    if name.endswith(".md"):
        name = name[:-3]
    name = Path(name).name
    return name or DEFAULT_TEMPLATE


def template_path(name: str) -> Path:
    sanitized = sanitize_template_name(name)
    path = template_dir() / f"{sanitized}.md"
    if not path.exists():
        raise ValueError(f"unknown template: {sanitized}")
    return path


def list_templates() -> list[str]:
    directory = template_dir()
    if not directory.exists():
        return []
    return sorted(path.stem for path in directory.glob("*.md"))


def load_template_text(name: str) -> str:
    return template_path(name).read_text(encoding=TEXT_ENCODING)


def tags_label(tags: list[str]) -> str:
    return ", ".join(tags) if tags else "none"


def new_item(
    prompt: str,
    max_iterations: int,
    template_name: str,
    objective: str,
    done_when: str,
    completion_promise: str,
    tags: list[str],
    note: str,
) -> dict:
    created_at = iso_now()
    item_id = str(uuid.uuid4())
    return {
        "id": item_id,
        "session_id": item_id,
        "prompt": prompt,
        "objective": objective or prompt,
        "done_when": done_when or DEFAULT_DONE_WHEN,
        "template": sanitize_template_name(template_name),
        "completion_promise": completion_promise or DEFAULT_PROMISE,
        "note": note or DEFAULT_NOTE,
        "tags": unique_strings(tags),
        "remaining": max_iterations,
        "max_iterations": max_iterations,
        "emitted_count": 0,
        "created_at": created_at,
        "updated_at": created_at,
    }


def archive_item(state: dict, item: dict, reason: str) -> None:
    archived = dict(item)
    archived["archived_reason"] = reason
    archived["archived_at"] = iso_now()
    archive = state.get("archive") or []
    archive.append(archived)
    state["archive"] = archive[-ARCHIVE_LIMIT:]


def promote_if_needed(state: dict) -> None:
    if state.get("active") is None and state.get("queue"):
        next_item = state["queue"].pop(0)
        next_item["updated_at"] = iso_now()
        state["active"] = next_item


def clamp_iterations(value: int, force: bool) -> int:
    if value <= 0:
        raise ValueError("max-iterations must be >= 1")
    if value > HARD_MAX_ITERATIONS and not force:
        raise ValueError(
            f"max-iterations exceeds hard cap ({HARD_MAX_ITERATIONS}); use --force to override"
        )
    return value


def read_prompt(args: argparse.Namespace) -> str:
    sources = [
        bool(args.prompt),
        bool(args.prompt_file),
        bool(args.prompt_stdin),
    ]
    if sum(sources) > 1:
        raise ValueError("use only one of --prompt, --prompt-file, or --prompt-stdin")
    if args.prompt:
        return str(args.prompt).strip()
    if args.prompt_file:
        prompt_path = Path(args.prompt_file)
        try:
            return prompt_path.read_text(encoding=TEXT_ENCODING).strip()
        except Exception as exc:
            raise ValueError(f"failed to read prompt file: {exc}") from exc
    if args.prompt_stdin:
        return sys.stdin.read().strip()
    return ""


def build_render_context(item: dict) -> dict:
    next_iteration = item["emitted_count"] + 1
    return {
        "objective": item["objective"],
        "prompt": item["prompt"],
        "done_when": item["done_when"],
        "completion_promise": item["completion_promise"],
        "iteration_label": f"{next_iteration} of {item['max_iterations']}",
        "remaining_iterations": str(item["remaining"]),
        "max_iterations": str(item["max_iterations"]),
        "session_id": item["session_id"],
        "tags": tags_label(item["tags"]),
        "note": item["note"],
    }


def render_wrapped_prompt(item: dict) -> str:
    template_text = load_template_text(item["template"])
    template = Template(template_text)
    return template.safe_substitute(build_render_context(item)).strip()


def summary_row(item: dict) -> dict:
    return {
        "id": item["id"],
        "session_id": item["session_id"],
        "template": item["template"],
        "objective": item["objective"],
        "remaining": item["remaining"],
        "max_iterations": item["max_iterations"],
        "tags": item["tags"],
        "created_at": item["created_at"],
        "updated_at": item["updated_at"],
    }


def emit_payload(item: dict, wrapped_prompt: str, finished: bool) -> dict:
    return {
        "id": item["id"],
        "session": item["session_id"],
        "prompt": item["prompt"],
        "wrapped_prompt": wrapped_prompt,
        "objective": item["objective"],
        "done_when": item["done_when"],
        "template": item["template"],
        "remaining": item["remaining"],
        "max_iterations": item["max_iterations"],
        "created_at": item["created_at"],
        "tags": item["tags"],
        "finished": finished,
    }


def parse_tags(raw_tags: list[str] | None) -> list[str]:
    if not raw_tags:
        return []
    tags = []
    for raw_tag in raw_tags:
        parts = [part.strip() for part in str(raw_tag).split(",")]
        tags.extend(part for part in parts if part)
    return unique_strings(tags)


def cmd_loop(args: argparse.Namespace) -> int:
    try:
        prompt = read_prompt(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not prompt:
        print("error: prompt is required", file=sys.stderr)
        return 2
    try:
        max_iterations = clamp_iterations(
            args.max_iterations or DEFAULT_MAX_ITERATIONS, args.force
        )
        template_path(args.template)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    state = load_state()
    item = new_item(
        prompt=prompt,
        max_iterations=max_iterations,
        template_name=args.template,
        objective=(args.objective or prompt).strip(),
        done_when=(args.done_when or DEFAULT_DONE_WHEN).strip(),
        completion_promise=(args.completion_promise or DEFAULT_PROMISE).strip(),
        tags=parse_tags(args.tag),
        note=(args.note or DEFAULT_NOTE).strip(),
    )
    queued = state.get("active") is not None
    if queued:
        state["queue"].append(item)
    else:
        state["active"] = item
    write_state(state)
    output = {
        "queued": queued,
        "state_dir": str(state_dir()),
        "queue_size": len(state.get("queue", [])),
        **summary_row(item),
    }
    if args.json:
        print(json.dumps(output, indent=2))
        return 0
    label = "Queued" if queued else "Started"
    print(f"{label} Ralph session {item['session_id']} using template {item['template']}.")
    return 0


def current_item(state: dict) -> dict | None:
    active = state.get("active")
    if active:
        return active
    promote_if_needed(state)
    return state.get("active")


def handle_finished_active(state: dict) -> None:
    active = state.get("active")
    if not active:
        return
    if active["remaining"] > 0:
        return
    archive_item(state, active, "completed")
    state["active"] = None
    promote_if_needed(state)


def cmd_next(args: argparse.Namespace) -> int:
    state = load_state()
    handle_finished_active(state)
    active = current_item(state)
    if not active:
        print("queue empty", file=sys.stderr)
        return 1
    wrapped_prompt = render_wrapped_prompt(active)
    active["emitted_count"] += 1
    active["remaining"] = max(0, active["remaining"] - 1)
    active["updated_at"] = iso_now()
    finished = active["remaining"] == 0
    payload = emit_payload(active, wrapped_prompt, finished)
    if finished:
        archive_item(state, active, "completed")
        state["active"] = None
        promote_if_needed(state)
    write_state(state)
    payload["queue_size"] = len(state.get("queue", []))
    payload["archived"] = finished
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(payload["prompt"] if args.raw else payload["wrapped_prompt"])
    return 0


def cmd_peek(args: argparse.Namespace) -> int:
    state = load_state()
    handle_finished_active(state)
    active = current_item(state)
    if not active:
        print("queue empty", file=sys.stderr)
        return 1
    wrapped_prompt = render_wrapped_prompt(active)
    payload = emit_payload(active, wrapped_prompt, active["remaining"] == 0)
    payload["queue_size"] = len(state.get("queue", []))
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(payload["prompt"] if args.raw else payload["wrapped_prompt"])
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state = load_state()
    handle_finished_active(state)
    active = current_item(state)
    queue = state.get("queue") or []
    archive = state.get("archive") or []
    payload = {
        "active": bool(active),
        "active_id": active.get("id") if active else None,
        "active_session": active.get("session_id") if active else None,
        "active_template": active.get("template") if active else None,
        "active_remaining": active.get("remaining") if active else 0,
        "active_max_iterations": active.get("max_iterations") if active else 0,
        "active_created_at": active.get("created_at") if active else None,
        "queue_size": len(queue),
        "archive_size": len(archive),
        "state_dir": str(state_dir()),
    }
    write_state(state)
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    if active:
        print(
            f"active session: {active['session_id']} "
            f"({active['template']} {active['remaining']}/{active['max_iterations']})"
        )
    else:
        print("active session: none")
    print(f"queued items: {len(queue)}")
    print(f"archived items: {len(archive)}")
    print(f"state dir: {state_dir()}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    state = load_state()
    handle_finished_active(state)
    payload = {
        "active": summary_row(state["active"]) if state.get("active") else None,
        "queue": [summary_row(item) for item in state.get("queue", [])],
        "archive": [summary_row(item) for item in state.get("archive", [])[-5:]],
        "state_dir": str(state_dir()),
    }
    write_state(state)
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    if payload["active"]:
        active = payload["active"]
        print(
            f"active: {active['session_id']} "
            f"{active['template']} {active['remaining']}/{active['max_iterations']} "
            f"{active['objective']}"
        )
    else:
        print("active: none")
    if payload["queue"]:
        print("queue:")
        for item in payload["queue"]:
            print(
                f"- {item['session_id']} {item['template']} "
                f"{item['remaining']}/{item['max_iterations']} {item['objective']}"
            )
    else:
        print("queue: empty")
    if payload["archive"]:
        print("recent archive:")
        for item in payload["archive"]:
            print(f"- {item['session_id']} {item['template']} {item['objective']}")
    return 0


def remove_matching(queue: list[dict], item_id: str) -> tuple[list[dict], list[dict]]:
    kept = []
    removed = []
    for item in queue:
        if item["id"] == item_id or item["session_id"] == item_id:
            removed.append(item)
        else:
            kept.append(item)
    return kept, removed


def cmd_cancel(args: argparse.Namespace) -> int:
    state = load_state()
    removed = []
    if args.id:
        active = state.get("active")
        if active and args.id in (active["id"], active["session_id"]):
            removed.append(active)
            state["active"] = None
        queue, queue_removed = remove_matching(state.get("queue", []), args.id)
        state["queue"] = queue
        removed.extend(queue_removed)
    else:
        if state.get("active"):
            removed.append(state["active"])
        removed.extend(state.get("queue", []))
        state["active"] = None
        state["queue"] = []
    for item in removed:
        archive_item(state, item, "cancelled")
    promote_if_needed(state)
    write_state(state)
    if args.json:
        print(
            json.dumps(
                {
                    "cancelled": [summary_row(item) for item in removed],
                    "queue_size": len(state.get("queue", [])),
                    "archive_size": len(state.get("archive", [])),
                },
                indent=2,
            )
        )
        return 0
    if args.id and not removed:
        print("No matching session found.")
        return 1
    print(f"Cancelled {len(removed)} Ralph session(s).")
    return 0


def cmd_template_list(args: argparse.Namespace) -> int:
    templates = list_templates()
    if args.json:
        print(json.dumps({"templates": templates}, indent=2))
        return 0
    for name in templates:
        print(name)
    return 0


def cmd_template_show(args: argparse.Namespace) -> int:
    try:
        content = load_template_text(args.name)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"name": sanitize_template_name(args.name), "content": content}, indent=2))
        return 0
    print(content.rstrip())
    return 0


def cmd_template_render(args: argparse.Namespace) -> int:
    try:
        prompt = read_prompt(args)
        if not prompt:
            raise ValueError("prompt is required")
        template_path(args.name)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    item = new_item(
        prompt=prompt,
        max_iterations=args.max_iterations or DEFAULT_MAX_ITERATIONS,
        template_name=args.name,
        objective=(args.objective or prompt).strip(),
        done_when=(args.done_when or DEFAULT_DONE_WHEN).strip(),
        completion_promise=(args.completion_promise or DEFAULT_PROMISE).strip(),
        tags=parse_tags(args.tag),
        note=(args.note or DEFAULT_NOTE).strip(),
    )
    wrapped_prompt = render_wrapped_prompt(item)
    payload = {
        "name": sanitize_template_name(args.name),
        "wrapped_prompt": wrapped_prompt,
        "objective": item["objective"],
        "done_when": item["done_when"],
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(wrapped_prompt)
    return 0


def add_prompt_source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--prompt", help="Prompt text")
    parser.add_argument("--prompt-file", help="Read prompt from a file")
    parser.add_argument(
        "--prompt-stdin",
        action="store_true",
        help="Read prompt from stdin",
    )


def add_render_arguments(parser: argparse.ArgumentParser) -> None:
    add_prompt_source_arguments(parser)
    parser.add_argument(
        "--objective",
        help="Concrete outcome Ralph should optimize for",
    )
    parser.add_argument(
        "--done-when",
        help="Verifiable completion condition",
    )
    parser.add_argument(
        "--completion-promise",
        default=DEFAULT_PROMISE,
        help="Promise token emitted only when work is complete",
    )
    parser.add_argument(
        "--tag",
        action="append",
        help="Optional tag(s), repeat or comma-separate",
    )
    parser.add_argument("--note", help="Extra operator note")
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help=f"Number of repeats (default {DEFAULT_MAX_ITERATIONS})",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Persistent Ralph Wiggum prompt loop for Codex",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    loop_parser = subparsers.add_parser("loop", help="Start or enqueue a Ralph session")
    add_render_arguments(loop_parser)
    loop_parser.add_argument(
        "--template",
        default=DEFAULT_TEMPLATE,
        help=f"Template to wrap the prompt with (default {DEFAULT_TEMPLATE})",
    )
    loop_parser.add_argument(
        "--force",
        action="store_true",
        help=f"Allow max-iterations above {HARD_MAX_ITERATIONS}",
    )
    loop_parser.set_defaults(func=cmd_loop)

    next_parser = subparsers.add_parser("next", help="Emit and advance the active session")
    next_parser.add_argument("--json", action="store_true", help="JSON output")
    next_parser.add_argument(
        "--raw",
        action="store_true",
        help="Print only the original prompt instead of the wrapped prompt",
    )
    next_parser.set_defaults(func=cmd_next)

    peek_parser = subparsers.add_parser("peek", help="Preview the active session without decrementing")
    peek_parser.add_argument("--json", action="store_true", help="JSON output")
    peek_parser.add_argument(
        "--raw",
        action="store_true",
        help="Print only the original prompt instead of the wrapped prompt",
    )
    peek_parser.set_defaults(func=cmd_peek)

    status_parser = subparsers.add_parser("status", help="Show queue status")
    status_parser.add_argument("--json", action="store_true", help="JSON output")
    status_parser.set_defaults(func=cmd_status)

    list_parser = subparsers.add_parser("list", help="List active, queued, and archived sessions")
    list_parser.add_argument("--json", action="store_true", help="JSON output")
    list_parser.set_defaults(func=cmd_list)

    cancel_parser = subparsers.add_parser("cancel", help="Cancel Ralph sessions")
    cancel_parser.add_argument("--id", help="Cancel one session by id or session_id")
    cancel_parser.add_argument("--json", action="store_true", help="JSON output")
    cancel_parser.set_defaults(func=cmd_cancel)

    clear_parser = subparsers.add_parser("clear", help="Alias for canceling all live sessions")
    clear_parser.add_argument("--json", action="store_true", help="JSON output")
    clear_parser.set_defaults(id=None, func=cmd_cancel)

    template_parser = subparsers.add_parser("template", help="Inspect and render Ralph templates")
    template_subparsers = template_parser.add_subparsers(dest="template_command", required=True)

    template_list_parser = template_subparsers.add_parser("list", help="List available templates")
    template_list_parser.add_argument("--json", action="store_true", help="JSON output")
    template_list_parser.set_defaults(func=cmd_template_list)

    template_show_parser = template_subparsers.add_parser("show", help="Print a template")
    template_show_parser.add_argument("name", help="Template name")
    template_show_parser.add_argument("--json", action="store_true", help="JSON output")
    template_show_parser.set_defaults(func=cmd_template_show)

    template_render_parser = template_subparsers.add_parser("render", help="Render a template without queueing it")
    template_render_parser.add_argument("name", help="Template name")
    add_render_arguments(template_render_parser)
    template_render_parser.set_defaults(func=cmd_template_render)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
